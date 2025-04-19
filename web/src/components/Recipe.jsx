/* eslint-disable react/prop-types */
import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Clock, Utensils, ArrowLeft } from 'lucide-react';
import Loading from './Loading';
import LikeButton from './LikeButton';
import RecipeCard from './RecipeCard';
import useLikes from '../useLikes';
import { getRecipe, getSimilar } from '../api';
import { formatMinutes } from '../utils';
import bgImage from './bg.svg';

const toList = (value, sep) => {
  if (Array.isArray(value)) return value.map(String);
  if (typeof value === 'string') return value.split(sep).map((s) => s.trim()).filter(Boolean);
  return [];
};

const formatInstructions = (instructions) => {
  const steps = toList(instructions, '.').filter((step) => step !== '|');
  const pairedSteps = [];
  for (let i = 0; i < steps.length; i += 2) {
    pairedSteps.push({
      stepNumber: Math.floor(i / 2) + 1,
      lineOne: steps[i],
      lineTwo: steps[i + 1] || '',
    });
  }
  return pairedSteps;
};

const Page = ({ children }) => (
  <div className="w-full min-h-screen" style={{ background: `url(${bgImage}) repeat`, backgroundSize: '500px 500px' }}>
    {children}
  </div>
);

const Recipe = () => {
  const { id } = useParams();
  const [state, setState] = useState({ status: 'loading', recipe: null, error: '' });
  const [similar, setSimilar] = useState({ status: 'loading', items: [], error: '' });
  const [attempt, setAttempt] = useState(0);
  const { liked, toggle } = useLikes();
  const numericId = Number(id);

  useEffect(() => {
    const controller = new AbortController();
    setState({ status: 'loading', recipe: null, error: '' });
    setSimilar({ status: 'loading', items: [], error: '' });
    window.scrollTo(0, 0);

    getRecipe(id, { signal: controller.signal })
      .then((recipe) => setState({ status: 'done', recipe, error: '' }))
      .catch((err) => {
        if (err.name !== 'AbortError') setState({ status: 'error', recipe: null, error: err.message, notFound: err.status === 404 });
      });

    getSimilar(id, { signal: controller.signal })
      .then((data) => setSimilar({ status: 'done', items: (data.recommendations || []).slice(0, 6), error: '' }))
      .catch((err) => {
        if (err.name !== 'AbortError') setSimilar({ status: 'error', items: [], error: err.message });
      });

    return () => controller.abort();
  }, [id, attempt]);

  if (state.status === 'loading') {
    return <Page><div className="text-center pt-96 pb-64"><Loading /></div></Page>;
  }

  if (state.status === 'error') {
    return (
      <Page>
        <div className="max-w-4xl mx-auto mt-16 p-6 bg-white border-2 border-black shadow-lg text-center">
          <h1 className="text-3xl font-bold mb-3">{state.notFound ? 'Recipe not found' : 'Something went wrong'}</h1>
          <p className="text-gray-700 mb-6" role="alert">{state.notFound ? 'That recipe may have been removed.' : state.error}</p>
          <div className="flex justify-center gap-3">
            {!state.notFound && (
              <button
                type="button"
                onClick={() => setAttempt((n) => n + 1)}
                className="bg-gray-800 text-white py-3 px-6 rounded-full text-lg font-semibold hover:bg-gray-700 transition duration-200"
              >
                Try again
              </button>
            )}
            <Link to="/" className="bg-gray-200 text-gray-800 py-3 px-6 rounded-full text-lg font-semibold hover:bg-gray-300 transition duration-200">
              Back to search
            </Link>
          </div>
        </div>
      </Page>
    );
  }

  const { recipe } = state;
  const ingredients = toList(recipe.cooking_ingredients, ',');
  const instructions = formatInstructions(recipe.cooking_instruction);

  return (
    <Page>
      <div className="max-w-4xl mx-auto p-6 bg-white border-2 border-black shadow-lg">
        <Link to="/" className="inline-flex items-center text-gray-700 hover:text-black mb-4">
          <ArrowLeft className="w-5 h-5 mr-1" /> Back to search
        </Link>
        <div className="flex items-start justify-between gap-4 mb-4">
          <h1 className="text-3xl font-bold text-dark-600">{recipe.name}</h1>
          <LikeButton liked={liked.includes(numericId)} onToggle={() => toggle(numericId)} className="shrink-0" />
        </div>
        <p className="text-gray-600 mb-6">{recipe.description}</p>
        {recipe.veg ?
          <p className="px-3 py-1 w-20 my-2 text-center rounded-full font-semibold bg-green-300 text-green-800">Veg</p> :
          <p className="px-3 py-1 w-24 my-2 text-center rounded-full font-semibold bg-red-300 text-red-800">Non-Veg</p>
        }

        {recipe.image && <img src={recipe.image} alt={recipe.name} className="w-full h-96 object-cover rounded-lg mb-6" />}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {[['Prep', recipe.prep_time], ['Cook', recipe.cook_time], ['Total', recipe.total_time]].map(([label, value]) => {
            const text = formatMinutes(value);
            return text ? (
              <div key={label} className="flex items-center">
                <Clock className="w-5 h-5 mr-2 text-dark-600" />
                <span>{label} {text}</span>
              </div>
            ) : null;
          })}
          {recipe.course && (
            <div className="flex items-center">
              <Utensils className="w-5 h-5 mr-2 text-dark-600" />
              <span>{recipe.course}</span>
            </div>
          )}
        </div>

        <div className="mb-6">
          <h2 className="text-2xl font-semibold mb-3 text-dark-600">Ingredients</h2>
          <ol className="list-decimal list-inside">
            {ingredients.map((ingredient, index) => (
              <li key={index} className="text-gray-700">{ingredient}</li>
            ))}
          </ol>
        </div>

        <div>
          <h2 className="text-2xl font-semibold mb-3 text-dark-600">Instructions</h2>
          <ol className="space-y-4">
            {instructions.map(({ stepNumber, lineOne, lineTwo }) => (
              <li key={stepNumber} className="text-gray-700">
                <div className="font-semibold mb-1">Step {stepNumber}:</div>
                <div className="ml-4">
                  <div>{lineOne}</div>
                  {lineTwo && <div className="mt-1">{lineTwo}</div>}
                </div>
              </li>
            ))}
          </ol>
        </div>

        <div className="mt-10">
          <h2 className="text-2xl font-semibold mb-3 text-dark-600">More like this</h2>
          {similar.status === 'loading' && <p className="text-gray-600">Finding similar recipes...</p>}
          {similar.status === 'error' && <p className="text-gray-700" role="alert">Could not load similar recipes. {similar.error}</p>}
          {similar.status === 'done' && similar.items.length === 0 && <p className="text-gray-600">No similar recipes found.</p>}
          {similar.items.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {similar.items.map((r) => (
                <RecipeCard key={r.id} recipe={r} liked={liked.includes(r.id)} onToggleLike={() => toggle(r.id)} />
              ))}
            </div>
          )}
        </div>

        <div className="mt-8 text-center">
          <h2 className="text-xl font-semibold">Enjoy!</h2>
          <div className="flex justify-center space-x-4 mt-2">
            <span className="text-lg">¡Disfruta!</span>
            <span className="text-lg">Bon appétit!</span>
            <span className="text-lg">Guten Appetit!</span>
            <span className="text-lg">Buon appetito!</span>
            <span className="text-lg">いただきます！(Itadakimasu!)</span>
          </div>
        </div>
      </div>
    </Page>
  );
};

export default Recipe;
