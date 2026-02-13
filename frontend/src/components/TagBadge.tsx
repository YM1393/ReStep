import type { PatientTag } from '../types';

interface TagBadgeProps {
  tag: PatientTag;
  onRemove?: (tagId: string) => void;
  size?: 'sm' | 'md';
}

export default function TagBadge({ tag, onRemove, size = 'sm' }: TagBadgeProps) {
  const sizeClass = size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-3 py-1';

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full font-medium ${sizeClass}`}
      style={{
        backgroundColor: `${tag.color}20`,
        color: tag.color,
        border: `1px solid ${tag.color}40`
      }}
    >
      {tag.name}
      {onRemove && (
        <button
          onClick={(e) => { e.stopPropagation(); onRemove(tag.id); }}
          className="ml-0.5 hover:opacity-70"
        >
          &times;
        </button>
      )}
    </span>
  );
}
