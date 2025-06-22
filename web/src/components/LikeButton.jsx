/* eslint-disable react/prop-types */
import { Heart } from 'lucide-react';

const LikeButton = ({ liked, onToggle, className = '' }) => (
  <button
    type="button"
    aria-pressed={liked}
    aria-label={liked ? 'Remove from liked recipes' : 'Like this recipe'}
    title={liked ? 'Liked' : 'Like'}
    onClick={(e) => {
      e.preventDefault();
      e.stopPropagation();
      onToggle();
    }}
    className={`inline-flex h-11 w-11 items-center justify-center rounded-full transition-colors hover:bg-slate-100 ${className}`}
  >
    <Heart
      size={20}
      strokeWidth={1.75}
      className={liked ? 'fill-ink text-ink' : 'text-slate-500'}
    />
  </button>
);

export default LikeButton;
