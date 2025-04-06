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
    className={`p-2 rounded-full bg-white border-2 border-slate-600 shadow-md hover:bg-gray-200 transition duration-200 focus:outline-none focus:ring-2 focus:ring-gray-500 ${className}`}
  >
    <Heart size={20} className={liked ? 'text-red-600 fill-red-600' : 'text-gray-700'} />
  </button>
);

export default LikeButton;
