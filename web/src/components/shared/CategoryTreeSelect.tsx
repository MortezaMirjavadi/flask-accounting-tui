import { useState, useMemo, useRef, useCallback } from "react";
import { ChevronRight, ChevronLeft, Check, ChevronsUpDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Input } from "@/components/ui/input";
import type { Category } from "@/types";

// Flatten tree to find a node by id
function findNode(nodes: Category[], id: number): Category | null {
  for (const node of nodes) {
    if (node.id === id) return node;
    if (node.children) {
      const found = findNode(node.children, id);
      if (found) return found;
    }
  }
  return null;
}

// Get all ancestor ids of a node (for auto-expanding)
function getAncestorIds(nodes: Category[], targetId: number, path: number[] = []): number[] | null {
  for (const node of nodes) {
    if (node.id === targetId) return path;
    if (node.children) {
      const result = getAncestorIds(node.children, targetId, [...path, node.id]);
      if (result) return result;
    }
  }
  return null;
}

// Filter tree by search query
function filterTree(nodes: Category[], query: string): Category[] {
  const q = query.toLowerCase();
  const result: Category[] = [];
  for (const node of nodes) {
    const childMatches = node.children ? filterTree(node.children, query) : [];
    const selfMatch = node.name.toLowerCase().includes(q);
    if (selfMatch || childMatches.length > 0) {
      result.push({
        ...node,
        children: selfMatch ? node.children : childMatches,
      });
    }
  }
  return result;
}

interface TreeNodeRowProps {
  node: Category;
  depth: number;
  selectedId: number | undefined;
  expandedIds: Set<number>;
  onToggle: (id: number) => void;
  onSelect: (node: Category) => void;
}

function TreeNodeRow({
  node,
  depth,
  selectedId,
  expandedIds,
  onToggle,
  onSelect,
}: TreeNodeRowProps) {
  const hasChildren = node.children && node.children.length > 0;
  const isExpanded = expandedIds.has(node.id);
  const isSelected = node.id === selectedId;
  const isRtl =
    typeof document !== "undefined" && document.documentElement.dir === "rtl";
  const Chevron = isRtl ? ChevronLeft : ChevronRight;

  return (
    <div>
      <button
        type="button"
        className={cn(
          "flex w-full items-center gap-2 px-2 py-1.5 text-sm transition-colors hover:bg-accent",
          isSelected && "bg-accent",
        )}
        style={{ paddingInlineStart: `${depth * 1.25 + 0.5}rem` }}
        onClick={() => onSelect(node)}
      >
        {/* Expand/Collapse */}
        <span
          className={cn(
            "flex h-4 w-4 shrink-0 items-center justify-center",
            !hasChildren && "invisible",
          )}
          onClick={(e) => {
            e.stopPropagation();
            if (hasChildren) onToggle(node.id);
          }}
        >
          <Chevron
            className={cn(
              "h-3 w-3 text-muted-foreground transition-transform",
              isExpanded && "rotate-90",
            )}
          />
        </span>

        {/* Name */}
        <span className={cn("flex-1 truncate text-start", isSelected && "font-medium")}>
          {node.name}
        </span>

        {/* Type badge */}
        <span
          className={cn(
            "shrink-0 rounded px-1 py-0.5 text-[9px] font-medium leading-none",
            node.type === "income"
              ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
              : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
          )}
        >
          {node.type === "income" ? "+" : "-"}
        </span>

        {/* Selected check */}
        {isSelected && <Check className="h-4 w-4 shrink-0 text-primary" />}
      </button>

      {hasChildren && isExpanded && (
        <div>
          {node.children!.map((child) => (
            <TreeNodeRow
              key={child.id}
              node={child}
              depth={depth + 1}
              selectedId={selectedId}
              expandedIds={expandedIds}
              onToggle={onToggle}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface CategoryTreeSelectProps {
  categories: Category[];
  value?: number;
  onChange: (id: number) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

export function CategoryTreeSelect({
  categories,
  value,
  onChange,
  placeholder = "انتخاب دسته‌بندی",
  disabled,
  className,
}: CategoryTreeSelectProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  // Auto-expand ancestors of selected node
  const [expandedIds, setExpandedIds] = useState<Set<number>>(() => {
    if (!value) return new Set();
    const ancestors = getAncestorIds(categories, value);
    return new Set(ancestors ?? []);
  });

  const handleOpenChange = useCallback(
    (isOpen: boolean) => {
      setOpen(isOpen);
      if (isOpen) {
        setSearch("");
        // Re-expand ancestors of selected node when opening
        if (value) {
          const ancestors = getAncestorIds(categories, value);
          if (ancestors) {
            setExpandedIds((prev) => {
              const next = new Set(prev);
              ancestors.forEach((id) => next.add(id));
              return next;
            });
          }
        }
      }
    },
    [value, categories],
  );

  const filtered = useMemo(() => {
    if (!search.trim()) return categories;
    const result = filterTree(categories, search);
    // Auto-expand all when searching
    if (search.trim()) {
      const ids = new Set<number>();
      function collect(nodes: Category[]) {
        for (const n of nodes) {
          if (n.children && n.children.length > 0) {
            ids.add(n.id);
            collect(n.children);
          }
        }
      }
      collect(result);
      setExpandedIds(ids);
    }
    return result;
  }, [categories, search]);

  const handleToggle = useCallback((id: number) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleSelect = useCallback(
    (node: Category) => {
      onChange(node.id);
      setOpen(false);
    },
    [onChange],
  );

  const selectedNode = value ? findNode(categories, value) : null;

  // Build a path label for the selected node
  const selectedPath = useMemo(() => {
    if (!value || !selectedNode) return null;
    const ancestors = getAncestorIds(categories, value);
    if (!ancestors || ancestors.length === 0) return selectedNode.name;
    const names = ancestors
      .map((id) => findNode(categories, id)?.name)
      .filter(Boolean);
    names.push(selectedNode.name);
    return names.join(" › ");
  }, [value, selectedNode, categories]);

  return (
    <Popover open={open} onOpenChange={handleOpenChange}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          disabled={disabled}
          className={cn(
            "h-9 w-full justify-between bg-transparent px-3 text-start font-normal",
            !value && "text-muted-foreground",
            className,
          )}
        >
          <span className="truncate">
            {selectedPath || placeholder}
          </span>
          <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className="w-[--radix-popover-trigger-width] p-0"
        align="start"
        dir="rtl"
      >
        <div className="flex flex-col">
          {/* Search */}
          <div className="border-b px-3 py-2">
            <Input
              placeholder="جستجو..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-8 border-0 p-0 text-sm focus-visible:ring-0"
            />
          </div>

          {/* Tree */}
          <div className="max-h-64 overflow-y-auto py-1">
            {filtered.length === 0 ? (
              <p className="py-4 text-center text-xs text-muted-foreground">
                دسته‌بندی‌ای یافت نشد
              </p>
            ) : (
              filtered.map((node) => (
                <TreeNodeRow
                  key={node.id}
                  node={node}
                  depth={0}
                  selectedId={value}
                  expandedIds={expandedIds}
                  onToggle={handleToggle}
                  onSelect={handleSelect}
                />
              ))
            )}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}
