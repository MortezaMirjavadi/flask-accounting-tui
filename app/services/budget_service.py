import sqlite3
from database import get_connection


class BudgetService:
    @staticmethod
    def get_period(cursor, period_id, user_id):
        cursor.execute(
            "SELECT * FROM budget_periods WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
            (period_id, user_id),
        )
        return cursor.fetchone()
    
    @staticmethod
    def get_item(cursor, item_id, user_id):
        cursor.execute(
            "SELECT bi.*, bp.user_id FROM budget_items bi "
            "JOIN budget_periods bp ON bi.budget_period_id = bp.id "
            "WHERE bi.id = ? AND bp.user_id = ? AND bi.deleted_at IS NULL AND bp.deleted_at IS NULL",
            (item_id, user_id),
        )
        return cursor.fetchone()
    
    @staticmethod
    def get_periods_with_items(user_id, year=None, month=None):
        conn = get_connection()
        cursor = conn.cursor()
        
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
            WHERE bp.user_id = ? AND bp.deleted_at IS NULL
        """
        params = [user_id]
        
        if year is not None:
            query += " AND bp.year = ?"
            params.append(year)
        if month is not None:
            query += " AND bp.month = ?"
            params.append(month)
        
        query += " ORDER BY bp.year DESC, bp.month DESC"
        
        cursor.execute(query, params)
        periods = cursor.fetchall()
        
        # Get all items in one query
        period_ids = [p["id"] for p in periods]
        items_by_period = {}
        
        if period_ids:
            placeholders = ",".join("?" * len(period_ids))
            cursor.execute(f"""
                SELECT 
                    bi.id,
                    bi.budget_period_id,
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
        
        conn.close()
        
        result = []
        for period in periods:
            result.append({
                "id": period["id"],
                "year": period["year"],
                "month": period["month"],
                "created_at": period["created_at"],
                "item_count": period["item_count"],
                "total_planned": period["total_planned"],
                "items": items_by_period.get(period["id"], [])
            })
        
        return result
    
    @staticmethod
    def create_period(user_id, year, month):
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO budget_periods (user_id, year, month) VALUES (?, ?, ?)",
                (user_id, year, month),
            )
            conn.commit()
            new_id = cursor.lastrowid
            conn.close()
            return {"id": new_id, "year": year, "month": month}, None
        except sqlite3.IntegrityError:
            cursor.execute(
                "SELECT id FROM budget_periods WHERE user_id = ? AND year = ? AND month = ? AND deleted_at IS NOT NULL",
                (user_id, year, month),
            )
            archived = cursor.fetchone()
            if archived is None:
                conn.close()
                return None, "Budget period already exists for this year/month"
            cursor.execute(
                "UPDATE budget_periods SET deleted_at = NULL WHERE id = ?",
                (archived["id"],),
            )
            conn.commit()
            restored_id = archived["id"]
            conn.close()
            return {"id": restored_id, "year": year, "month": month}, None
    
    @staticmethod
    def delete_period(period_id, user_id):
        conn = get_connection()
        cursor = conn.cursor()
        
        if BudgetService.get_period(cursor, period_id, user_id) is None:
            conn.close()
            return False, "Budget period not found"
        
        cursor.execute(
            "UPDATE budget_items SET deleted_at = CURRENT_TIMESTAMP WHERE budget_period_id = ? AND deleted_at IS NULL",
            (period_id,),
        )
        cursor.execute(
            "UPDATE budget_periods SET deleted_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
            (period_id, user_id),
        )
        conn.commit()
        conn.close()
        return True, None
