/* eslint-disable no-unused-vars */
import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Clock, Users, ChefHat, Utensils } from 'lucide-react';
import Loading from './Loading';
import bgImage from './bg.svg';

const Recipe = () => {
  const location = useLocation();
  const [RecipeId, setRecipeId] = useState(null);
  const [recipe, setRecipe] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const id = params.get('name');
    if (id) {
      setRecipeId(id);
      fetchRecipe(id);
    }
  }, [location]);

  const fetchRecipe = async (id) => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_ENDPOINT}/api/recipe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name: id })
      });
      if (!response.ok) {
        throw new Error('Failed to fetch recipe');
      }

      const data = await response.json();
      setTimeout(() => {
        setRecipe(data);
        setLoading(false);
      }, 100);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  const formatInstructions = (instructions) => {
    const steps = instructions
      .split('.')
      .map(step => step.trim())
      .filter(step => step && step !== '|');

    const pairedSteps = [];
    for (let i = 0; i < steps.length; i += 2) {
      pairedSteps.push({
        stepNumber: Math.floor(i / 2) + 1,
        lineOne: steps[i],
        lineTwo: steps[i + 1] || ''
      });
    }

    return pairedSteps;
  };

  if (loading) return <div className="text-center mt-96 pb-64"><Loading /></div>;
  if (error) return <div className="text-center mt-8 text-red-500">Error: {error}</div>;
  if (!recipe) return <div className="text-center mt-8">No recipe data available</div>;

  const formattedInstructions = formatInstructions(recipe.cooking_instruction);

  return (
    <div className="w-full min-h-screen" style={{
        background: `url(${bgImage}) repeat`,
        backgroundSize: '500px 500px'
      }}>
      <div className="max-w-4xl mx-auto p-6 bg-white border-2 border-black shadow-lg">
        <h1 className="text-3xl font-bold mb-4 text-dark-600">{recipe.name}</h1>
        <p className="text-gray-600 mb-6">{recipe.description}</p>
        {recipe.veg ? 
          <p className="px-3 py-1 w-20 my-2 text-center rounded-full font-semibold bg-green-300 text-green-800">Veg</p> : 
          <p className="px-3 py-1 w-24 my-2 text-center rounded-full font-semibold bg-red-300 text-red-800">Non-Veg</p>
        }

        <img src={recipe.image} alt={recipe.name} className="w-full h-96 object-cover rounded-lg mb-6" />

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="flex items-center">
            <Clock className="w-5 h-5 mr-2 text-dark-600" />
            <span>{recipe.cooking_time}</span>
          </div>
          <div className="flex items-center">
            <Users className="w-5 h-5 mr-2 text-dark-600" />
            <span>{recipe.serving_size}</span>
          </div>
          <div className="flex items-center">
            <ChefHat className="w-5 h-5 mr-2 text-dark-600" />
            <span>{recipe.difficulty}</span>
          </div>
          <div className="flex items-center">
            <Utensils className="w-5 h-5 mr-2 text-dark-600" />
            <span>{recipe.course}</span>
          </div>
        </div>

        <div className="mb-6">
          <h2 className="text-2xl font-semibold mb-3 text-dark-600">Ingredients</h2>
          <ol className="list-decimal list-inside">
            {recipe.cooking_ingredients.split(',').map((ingredient, index) => (
              <li key={index} className="text-gray-700">{ingredient.trim()}</li>
            ))}
          </ol>
        </div>

        <div>
          <h2 className="text-2xl font-semibold mb-3 text-dark-600">Instructions</h2>
          <ol className="space-y-4">
            {formattedInstructions.map(({ stepNumber, lineOne, lineTwo }) => (
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

        {/* Enjoy Section */}
        <div className="mt-8 text-center">
          <h2 className="text-xl font-semibold">Enjoy!</h2>
          <div className="flex justify-center space-x-4 mt-2">
            <span className="text-lg">¡Disfruta!</span> {/* Spanish */}
            <span className="text-lg">Bon appétit!</span> {/* French */}
            <span className="text-lg">Guten Appetit!</span> {/* German */}
            <span className="text-lg">Buon appetito!</span> {/* Italian */}
            <span className="text-lg">いただきます！(Itadakimasu!)</span> {/* Japanese */}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Recipe;
