import { useState, useCallback } from "react";
import { ChevronRight, ChevronLeft, Plus, Pencil, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Category } from "@/types";

interface TreeNodeProps {
  node: Category;
  depth: number;
  expandedIds: Set<number>;
  onToggle: (id: number) => void;
  onAddChild?: (parent: Category) => void;
  onEdit?: (node: Category) => void;
  onDelete?: (node: Category) => void;
}

function TreeNode({
  node,
  depth,
  expandedIds,
  onToggle,
  onAddChild,
  onEdit,
  onDelete,
}: TreeNodeProps) {
  const hasChildren = node.children && node.children.length > 0;
  const isExpanded = expandedIds.has(node.id);
  const isRtl =
    typeof document !== "undefined" && document.documentElement.dir === "rtl";
  const Chevron = isRtl ? ChevronLeft : ChevronRight;

  return (
    <div>
      <div
        className={cn(
          "group flex items-center gap-2 rounded-md px-2 py-1.5 transition-colors hover:bg-muted/50",
        )}
        style={{
          paddingInlineStart: `${depth * 1.5 + 0.5}rem`,
        }}
      >
        {/* Expand/Collapse toggle */}
        <button
          type="button"
          className={cn(
            "flex h-5 w-5 shrink-0 items-center justify-center rounded-sm transition-colors hover:bg-muted",
            !hasChildren && "invisible",
          )}
          onClick={() => onToggle(node.id)}
        >
          <Chevron
            className={cn(
              "h-3.5 w-3.5 text-muted-foreground transition-transform",
              isExpanded && "rotate-90",
            )}
          />
        </button>

        {/* Category name */}
        <span className="flex-1 truncate text-sm font-medium">{node.name}</span>

        {/* Type badge */}
        <span
          className={cn(
            "shrink-0 rounded-md px-1.5 py-0.5 text-[10px] font-medium",
            node.type === "income"
              ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
              : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
          )}
        >
          {node.type === "income" ? "درآمد" : "هزینه"}
        </span>

        {/* Action buttons */}
        <div className="flex shrink-0 items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
          {onAddChild && (
            <button
              type="button"
              className="flex h-7 w-7 items-center justify-center rounded-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              title="زیردسته‌بندی جدید"
              onClick={() => onAddChild(node)}
            >
              <Plus className="h-3.5 w-3.5" />
            </button>
          )}
          {onEdit && (
            <button
              type="button"
              className="flex h-7 w-7 items-center justify-center rounded-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              title="ویرایش"
              onClick={() => onEdit(node)}
            >
              <Pencil className="h-3.5 w-3.5" />
            </button>
          )}
          {onDelete && (
            <button
              type="button"
              className="flex h-7 w-7 items-center justify-center rounded-sm text-destructive/70 transition-colors hover:bg-destructive/10 hover:text-destructive"
              title="حذف"
              onClick={() => onDelete(node)}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Children */}
      {hasChildren && isExpanded && (
        <div>
          {node.children!.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              depth={depth + 1}
              expandedIds={expandedIds}
              onToggle={onToggle}
              onAddChild={onAddChild}
              onEdit={onEdit}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface TreeViewProps {
  nodes: Category[];
  onAddChild?: (parent: Category) => void;
  onEdit?: (node: Category) => void;
  onDelete?: (node: Category) => void;
  className?: string;
  defaultExpanded?: boolean;
}

export function TreeView({
  nodes,
  onAddChild,
  onEdit,
  onDelete,
  className,
  defaultExpanded = false,
}: TreeViewProps) {
  const [expandedIds, setExpandedIds] = useState<Set<number>>(() => {
    if (!defaultExpanded) return new Set();
    const ids = new Set<number>();
    function collect(nodes: Category[]) {
      for (const node of nodes) {
        if (node.children && node.children.length > 0) {
          ids.add(node.id);
          collect(node.children);
        }
      }
    }
    collect(nodes);
    return ids;
  });

  const handleToggle = useCallback((id: number) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  if (!nodes || nodes.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        دسته‌بندی‌ای وجود ندارد
      </p>
    );
  }

  return (
    <div className={cn("space-y-0.5", className)}>
      {nodes.map((node) => (
        <TreeNode
          key={node.id}
          node={node}
          depth={0}
          expandedIds={expandedIds}
          onToggle={handleToggle}
          onAddChild={onAddChild}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
}
