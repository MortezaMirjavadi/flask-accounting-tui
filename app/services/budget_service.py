import psycopg2
import jdatetime
from database import get_connection, release_connection


class BudgetService:
    @staticmethod
    def get_period(cursor, period_id, user_id):
        cursor.execute(
            "SELECT * FROM budget_periods WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
            (period_id, user_id),
        )
        return cursor.fetchone()
    
    @staticmethod
    def get_item(cursor, item_id, user_id):
        cursor.execute(
            "SELECT bi.*, bp.user_id FROM budget_items bi "
            "JOIN budget_periods bp ON bi.budget_period_id = bp.id "
            "WHERE bi.id = %s AND bp.user_id = %s AND bi.deleted_at IS NULL AND bp.deleted_at IS NULL",
            (item_id, user_id),
        )
        return cursor.fetchone()
    
    @staticmethod
    def get_periods_with_items(user_id, year=None, month=None):
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Get periods with aggregated data
            query = """
                SELECT 
                    bp.id,
                    bp.year,
                    bp.month,
                    bp.created_at,
                    COALESCE(bi.item_count, 0) as item_count,
                    COALESCE(bi.total_planned, 0) as total_planned
                FROM budget_periods bp
                LEFT JOIN (
                    SELECT 
                        budget_period_id, 
                        COUNT(*) as item_count,
                        SUM(planned_amount) as total_planned
                    FROM budget_items
                    WHERE deleted_at IS NULL
                    GROUP BY budget_period_id
                ) bi ON bp.id = bi.budget_period_id
                WHERE bp.user_id = %s AND bp.deleted_at IS NULL
            """
            params = [user_id]
            
            if year is not None:
                query += " AND bp.year = %s"
                params.append(year)
            if month is not None:
                query += " AND bp.month = %s"
                params.append(month)
            
            query += " ORDER BY bp.year DESC, bp.month DESC"
            
            cursor.execute(query, params)
            periods = cursor.fetchall()
            
            # Get all items in one query (include category_id for actual lookup)
            period_ids = [p["id"] for p in periods]
            items_by_period = {}

            if period_ids:
                placeholders = ",".join(["%s"] * len(period_ids))
                cursor.execute(f"""
                    SELECT
                        bi.id,
                        bi.budget_period_id,
                        bi.category_id,
                        bi.planned_amount,
                        bi.notes,
                        c.name as category_name
                    FROM budget_items bi
                    JOIN categories c ON bi.category_id = c.id
                    WHERE bi.budget_period_id IN ({placeholders}) AND bi.deleted_at IS NULL
                    ORDER BY bi.budget_period_id, c.name
                """, period_ids)

                for item in cursor.fetchall():
                    pid = item["budget_period_id"]
                    items_by_period.setdefault(pid, []).append(dict(item))

            # Compute actual spending from transactions for each (year, month) pair
            # by converting Jalali year/month → Gregorian date range
            unique_ym = {(p["year"], p["month"]) for p in periods}
            # actual_map[(jalali_year, jalali_month, category_id)] = actual_amount
            actual_map = {}

            for y, m in unique_ym:
                start_jdate = jdatetime.date(y, m, 1)
                if m == 12:
                    end_jdate = jdatetime.date(y + 1, 1, 1) - jdatetime.timedelta(days=1)
                else:
                    end_jdate = jdatetime.date(y, m + 1, 1) - jdatetime.timedelta(days=1)
                start_greg = start_jdate.togregorian()
                end_greg = end_jdate.togregorian()

                cursor.execute(
                    """
                    SELECT t.category_id, COALESCE(SUM(t.amount), 0) as actual_amount
                    FROM transactions t
                    WHERE t.user_id = %s AND t.date >= %s AND t.date <= %s
                    GROUP BY t.category_id
                    """,
                    (user_id, start_greg, end_greg),
                )
                for row in cursor.fetchall():
                    actual_map[(y, m, row["category_id"])] = float(row["actual_amount"])

            # Attach actual_amount to each item and compute period totals
            result = []
            for period in periods:
                pid = period["id"]
                py, pm = period["year"], period["month"]
                items = items_by_period.get(pid, [])
                total_actual = 0.0

                for item in items:
                    cat_id = item.get("category_id")
                    actual = actual_map.get((py, pm, cat_id), 0.0)
                    item["actual_amount"] = actual
                    total_actual += actual

                result.append({
                    "id": pid,
                    "year": py,
                    "month": pm,
                    "created_at": period["created_at"],
                    "item_count": period["item_count"],
                    "total_planned": float(period["total_planned"]) if period["total_planned"] else 0,
                    "total_actual": total_actual,
                    "items": items,
                })
            
            return result
        finally:
            cursor.close()
            release_connection(conn)
    
    @staticmethod
    def create_period(user_id, year, month):
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO budget_periods (user_id, year, month) VALUES (%s, %s, %s) RETURNING id",
                (user_id, year, month),
            )
            new_id = cursor.fetchone()['id']
            conn.commit()
            return {"id": new_id, "year": year, "month": month}, None
        except psycopg2.IntegrityError:
            conn.rollback()
            cursor.execute(
                "SELECT id FROM budget_periods WHERE user_id = %s AND year = %s AND month = %s AND deleted_at IS NOT NULL",
                (user_id, year, month),
            )
            archived = cursor.fetchone()
            if archived is None:
                return None, "دوره بودجه برای این سال/ماه قبلاً ثبت شده است"
            cursor.execute(
                "UPDATE budget_periods SET deleted_at = NULL WHERE id = %s",
                (archived["id"],),
            )
            conn.commit()
            restored_id = archived["id"]
            return {"id": restored_id, "year": year, "month": month}, None
        except Exception as e:
            conn.rollback()
            return None, str(e)
        finally:
            cursor.close()
            release_connection(conn)
    
    @staticmethod
    def delete_period(period_id, user_id):
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            if BudgetService.get_period(cursor, period_id, user_id) is None:
                return False, "دوره بودجه یافت نشد"
            
            cursor.execute(
                "UPDATE budget_items SET deleted_at = CURRENT_TIMESTAMP WHERE budget_period_id = %s AND deleted_at IS NULL",
                (period_id,),
            )
            cursor.execute(
                "UPDATE budget_periods SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
                (period_id, user_id),
            )
            conn.commit()
            return True, None
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            cursor.close()
            release_connection(conn)
