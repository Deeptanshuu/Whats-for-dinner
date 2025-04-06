/* eslint-disable react/prop-types */
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Clock, Utensils } from 'lucide-react';
import LikeButton from './LikeButton';
import { formatMinutes } from '../utils';

function RecipeCard({ recipe, liked, onToggleLike, newTab = false }) {
  const { id, title, total_time, image, veg, cuisine, course } = recipe;
  const [imgFailed, setImgFailed] = useState(false);
  const time = formatMinutes(total_time);
  const meta = [cuisine, course].filter(Boolean).join(' | ');

  return (
    <div className="w-full h-full m-auto bg-white border-2 border-slate-600 shadow-xl shadow-stone-400 rounded-lg flex flex-col">
      <div className="relative">
        {image && !imgFailed ? (
          <img
            src={image}
            alt={title}
            onError={() => setImgFailed(true)}
            className="w-full h-[250px] object-cover  rounded-tr-lg rounded-tl-lg rounded-b-none border-slate-800 mb-5" />
        ) : (
          <div className="w-full h-[250px] bg-gray-200 flex items-center justify-center rounded-tr-lg rounded-tl-lg mb-5">
            <Utensils className="text-gray-400" size={48} />
          </div>
        )}
        <LikeButton liked={liked} onToggle={onToggleLike} className="absolute top-3 right-3" />
      </div>
      <div className="p-4">
        <h2 className="text-xl font-semibold mb-2">{title}</h2>
        {meta && <p className="text-gray-600 mb-4">{meta}</p>}
      </div>
      <div className="px-4 flex-grow">
        {veg ? <p className="px-3 py-1 w-16 my-2 text-center text-m rounded-full font-semibold bg-green-300 text-green-800">Veg</p> : <p className="px-3 py-1 w-24 my-2 text-center rounded-full font-semibold bg-red-300 text-red-800">Non-Veg</p>}
      </div>
      <div className="p-4 flex justify-between items-center border-t-2 border-gray-400">
        {time && (
          <span className="flex items-center px-2 py-1 text-s font-semibold rounded-full bg-gray-100 text-gray-800">
            <Clock className="mr-1" size={16} />
            {time}
          </span>
        )}
        <Link
          to={`/recipe/${id}`}
          target={newTab ? '_blank' : undefined}
          rel={newTab ? 'noopener noreferrer' : undefined}
          className={`${time ? 'w-1/2' : 'w-full'} text-center bg-gray-800 text-white text-s py-3 px-4 rounded-full text-lg font-semibold hover:bg-gray-700 transition duration-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-opacity-50`}
        >
          See Recipe
        </Link>
      </div>
    </div>
  );
}

export default RecipeCard;
