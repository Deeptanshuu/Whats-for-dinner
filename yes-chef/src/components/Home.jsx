import React, { useState } from 'react';
import { X, ChevronDown, ChevronUp, Search } from 'lucide-react';
import { Clock, Utensils } from 'lucide-react'

const Home = () => {
  const [selectedIngredients, setSelectedIngredients] = useState([]);
  const [selectedCuisines, setSelectedCuisines] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState('');
  const [selectedCravings, setSelectedCravings] = useState([]);
  const [expandedSections, setExpandedSections] = useState({
    ingredients: true,
    cuisines: false,
    courses: false,
    cravings: false,
  });
  const [searchTerm, setSearchTerm] = useState('');

  const ingredients = [
    'flour 🌾', 'sugar 🍬', 'eggs 🥚', 'chocolate chips 🍫', 'butter 🧈', 'vanilla extract 🌼',
    'rice noodles 🍜', 'tofu 🍶', 'bean sprouts 🌱', 'peanuts 🥜', 'lime 🍋', 'fish sauce 🐟',
    'tamarind paste 🌰', 'garlic 🧄', 'shallots 🧅', 'chicken 🍗', 'onions 🧅', 'tomatoes 🍅',
    'coconut milk 🥥', 'curry paste 🍛', 'ginger 🍂', 'cilantro 🌿', 'cocoa powder 🍫', 'milk 🥛',
    'vegetable oil 🌻', 'baking powder 🥄', 'salt 🧂', 'ground beef 🥩', 'pasta 🍝', 'carrots 🥕',
    'celery 🌿', 'red wine 🍷', 'beef broth 🍲', 'noodles 🍜', 'thyme 🌿', 'parsley 🌿', 'apples 🍎',
    'cinnamon 🍂', 'nutmeg 🍂', 'lemon juice 🍋', 'mixed vegetables 🥗', 'vegetable broth 🥣',
    'sushi rice 🍚', 'nori 🍙', 'fish (salmon/tuna) 🐟', 'cucumber 🥒', 'avocado 🥑', 'rice vinegar 🍚',
    'wasabi 🌶️', 'soy sauce 🍶', 'romaine lettuce 🥬', 'croutons 🥖', 'parmesan cheese 🧀', 'caesar dressing 🥗',
    'anchovies 🐟', 'cream 🥛', 'basil 🌿', 'taco shells 🌮', 'lettuce 🥬', 'cheese 🧀', 'sour cream 🍶',
    'taco seasoning 🌶️', 'sesame oil 🌻', 'rice 🍚', 'pie crust 🥧', 'lemons 🍋', 'cornstarch 🌽',
    'arborio rice 🍚', 'mushrooms 🍄', 'white wine 🍷', 'pork ribs 🍖', 'bbq sauce 🍖', 'brown sugar 🍬',
    'paprika 🌶️', 'garlic powder 🧄', 'onion powder 🧅', 'cucumbers 🥒', 'red onions 🧅', 'feta cheese 🧀',
    'olives 🫒', 'olive oil 🌿', 'oregano 🌿', 'yogurt 🥛', 'tomato sauce 🍅', 'garam masala 🌶️', 'bananas 🍌',
    'baking soda 🥄', 'beef strips 🥩', 'egg noodles 🍜', 'fresh mozzarella 🧀', 'balsamic vinegar 🍶',
    'beef/chicken 🥩🍗', 'herbs 🌿', 'chili 🌶️', 'star anise 🌟', 'ladyfingers 🍰', 'espresso ☕', 'mascarpone cheese 🧀',
    'chickpeas 🌱', 'cumin 🌿', 'coriander 🌿', 'corn tortillas 🌽', 'chicken/beef/cheese 🍗🥩🧀', 'enchilada sauce 🌶️',
    'red onion 🧅', 'beef 🥩', 'broccoli 🥦', 'red bell pepper 🌶️', 'potatoes 🥔', 'rice paper wrappers 🍚',
    'pork/shrimp/vegetables 🍖🍤🥗', 'vermicelli noodles 🍜', 'mint 🌿', 'eggplant 🍆', 'zucchini 🥒', 'bell peppers 🌶️',
    'assorted vegetables 🥗', 'sausage 🌭', 'shrimp 🍤', 'cajun seasoning 🌶️', 'ground beef/turkey 🥩🦃',
    'kidney beans 🌱', 'black beans 🌱', 'chili powder 🌶️', 'beans (black beans, pinto beans) 🌱',
    'meat (chicken, steak, carnitas) 🍗🥩', 'salsa 🌶️', 'guacamole 🥑', 'bacon 🥓', 'hard-boiled egg 🥚', 'cashews 🥜',
    'rice vinegar 🍚', 'chili paste 🌶️', 'nutritional yeast 🌾', 'black pepper 🌶️', 'vegetables (onion, bell pepper, spinach) 🧅🌶️🌿',
    'lentils 🌱', 'herbs (thyme, bay leaf) 🌿', 'salmon fillet 🐟', 'lemon slices 🍋', 'fresh herbs (dill, parsley) 🌿',
    'pepper 🌶️', 'quinoa 🍚', 'cherry tomatoes 🍅', 'chicken breast 🍗', 'breadcrumbs 🥖', 'mozzarella cheese 🧀',
    'lasagna noodles 🍜', 'ricotta cheese 🧀', 'spinach 🌿', 'beef chuck 🥩', 'Guinness beer 🍺', 'dashi stock 🍲',
    'miso paste 🍲', 'wakame seaweed 🌿', 'green onions 🧅', 'chicken thighs 🍗', 'pita bread 🥖', 'turmeric 🌿',
    'basmati rice 🍚', 'biryani spices 🌿', 'saffron 🌼', 'white fish 🐟', 'tartar sauce 🐟', 'lemon wedges 🍋',
    'cauliflower 🥦', 'blue cheese dressing 🥗', 'beef slices 🥩', 'pizza dough 🍕', 'tortillas 🌮', 'bell peppers 🌶️',
    'beef sirloin 🥩', 'green onions 🧅', 'tempura batter 🍤', 'dipping sauce 🥣', 'clams 🐚', 'heavy cream 🥛',
    'phyllo dough 🥐', 'dill 🌿', 'beef tenderloin 🥩', 'mushroom duxelles 🍄', 'prosciutto 🥓', 'puff pastry 🥐',
    'dijon mustard 🌶️', 'maple syrup 🍁', 'almond milk 🥛'
  ];


  const cuisines = [
    'American 🍔', 'Thai 🇹🇭', 'Indian 🇮🇳', 'International 🌎', 'Italian 🍝', 'Japanese 🍣',
    'Mexican 🌮', 'Asian 🥢', 'Greek 🇬🇷', 'Russian 🇷🇺', 'Vietnamese 🇻🇳', 'Middle Eastern 🥙',
    'French 🇫🇷', 'Vegan 🌱', 'Mediterranean 🌊', 'Italian-American 🍕', 'Irish 🇮🇪',
    'British 🇬🇧', 'Korean 🇰🇷'
  ];


  const courses = [
    'Dessert 🍰', 'Main Course 🍽️', 'Breakfast 🍳', 'Soup 🍜', 'Appetizer 🥟', 'Salad 🥗', 'Side Dish 🍲'
  ];


  const cravings = ['Sweet🍦', 'Savory😋', 'Spicy🌶️'];

  const toggleSection = (section) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const handleIngredientToggle = (ingredient) => {
    setSelectedIngredients(prev =>
      prev.includes(ingredient)
        ? prev.filter(i => i !== ingredient)
        : [...prev, ingredient]
    );
  };

  const handleCuisineChange = (cuisine) => {
    setSelectedCuisines(prev =>
      prev.includes(cuisine)
        ? prev.filter(c => c !== cuisine)
        : [...prev, cuisine]
    );
  };

  const handleCourseChange = (course) => {
    setSelectedCourse(course);
  };

  const handleCravingChange = (craving) => {
    setSelectedCravings(prev =>
      prev.includes(craving)
        ? prev.filter(c => c !== craving)
        : [...prev, craving]
    );
  };

  const filteredIngredients = ingredients.filter(ingredient =>
    ingredient.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const exampleRecipes = [
    {
      title: "Spaghetti Carbonara",
      description: "A classic Italian pasta dish with eggs, cheese, and pancetta",
      cookTime: 30,
      servings: 4,
      difficulty: "Medium",
      image: "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=870&q=80"
    },
    {
      title: "Chicken Stir Fry",
      description: "Quick and easy Asian-inspired dish with vegetables",
      cookTime: 20,
      servings: 3,
      difficulty: "Easy",
      image: "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=870&q=80"
    },
    {
      title: "Beef Wellington",
      description: "Luxurious dish of beef tenderloin wrapped in puff pastry",
      cookTime: 120,
      servings: 6,
      difficulty: "Hard",
      image: "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=870&q=80"
    },
    {
      title: "Beef Wellington",
      description: "Luxurious dish of beef tenderloin wrapped in puff pastry",
      cookTime: 120,
      servings: 6,
      difficulty: "Hard",
      image: "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=870&q=80"
    },
    {
      title: "Beef Wellington",
      description: "Luxurious dish of beef tenderloin wrapped in puff pastry",
      cookTime: 120,
      servings: 6,
      difficulty: "Hard",
      image: "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=870&q=80"
    },
    {
      title: "Beef Wellington",
      description: "Luxurious dish of beef tenderloin wrapped in puff pastry",
      cookTime: 120,
      servings: 6,
      difficulty: "Hard",
      image: "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=870&q=80"
    }
  ];

  const RecipeCard = ({ title, description, cookTime, servings, difficulty, image }) => (
    <div className="w-auto h-200 m-10 bg-white rounded-lg shadow-md overflow-hidden flex flex-col">
      <div className="p-4">
        <img
          src={image}
          alt="Recipe"
          className="w-full h-40 object-cover mb-4"
        />
      </div>
      <div className="p-4">
        <h2 className="text-xl font-semibold mb-2">{title}</h2>
        <p className="text-gray-600 mb-4">{description}</p>
      </div>
      <div className="px-4 flex-grow">
        <div className="flex items-center mb-2">
          <Clock className="mr-2 text-gray-500" size={24} />
          <span className="text-sm text-gray-700">{cookTime} mins</span>
        </div>
        <div className="flex items-center mb-2">
          <Utensils className="mr-2 text-gray-500" size={24} />
          <span className="text-sm text-gray-700">{servings} servings</span>
        </div>
      </div>
      <div className="p-4 flex justify-between items-center border-t border-gray-300">
        <span className={`px-2 py-1 text-s font-semibold rounded-full 
          ${difficulty === 'Easy' ? 'bg-green-100 text-green-800' :
            difficulty === 'Medium' ? 'bg-yellow-100 text-yellow-800' :
              'bg-red-100 text-red-800'
          }`}>
          {difficulty}
        </span>
        <button type="button" class="w-1/4 bg-gray-800 text-white text-s py-3 px-4 rounded-full text-lg font-semibold hover:bg-gray-700 transition duration-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-opacity-50" onClick={() => window.open("https://www.youtube.com/watch?v=dQw4w9WgXcQ")}>See Recipe</button>
      </div>
    </div>
  );


  return (
    <>
      <div className="home flex flex-row bg-gray-200">
        <div className="search-menu w-1/3 items-center p-5 bg-gray-200 overflow-auto">
          <h2 className="text-3xl p-3 font-bold mb-6 text-gray-800">What's for Dinner ?</h2>

          {/* Ingredients Section */}
          <div className="mb-8">
            <button
              className="flex items-center justify-between w-full p-3 bg-gray-300 rounded-lg text-lg font-semibold text-white-700 hover:bg-gray-200 transition duration-200"
              onClick={() => toggleSection('ingredients')}
            >
              <span>Ingredients</span>
              {expandedSections.ingredients ? <ChevronUp size={24} /> : <ChevronDown size={24} />}
            </button>
            {expandedSections.ingredients && (
              <div className="mt-4">
                <div className="relative mb-4">
                  <input
                    type="text"
                    placeholder="Search ingredients..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full p-2 pl-10 pr-4 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <Search className="absolute left-3 top-2.5 text-gray-400" size={20} />
                </div>
                <div className="flex max-h-80 overflow-auto flex-wrap gap-2">
                  {filteredIngredients.map(ingredient => (
                    <button
                      key={ingredient}
                      onClick={() => handleIngredientToggle(ingredient)}
                      className={`px-3 py-1 rounded-full text-m font-medium transition duration-200 ${selectedIngredients.includes(ingredient)
                          ? 'bg-blue-500 text-white'
                          : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                        }`}
                    >
                      {ingredient}
                      {selectedIngredients.includes(ingredient) && (
                        <X size={14} className="inline-block ml-1" />
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Cuisines Section */}
          <div className="mb-8">
            <button
              className="flex items-center justify-between w-full p-3 bg-gray-300 rounded-lg text-lg font-semibold text-white-700 hover:bg-gray-200 transition duration-200"
              onClick={() => toggleSection('cuisines')}
            >
              <span>Cuisines</span>
              {expandedSections.cuisines ? <ChevronUp size={24} /> : <ChevronDown size={24} />}
            </button>
            {expandedSections.cuisines && (
              <div className="flex p-3 overflow-auto flex-wrap gap-2">
                {cuisines.map(ingredient => (
                  <button
                    key={ingredient}
                    onClick={() => handleIngredientToggle(ingredient)}
                    className={`px-3 py-1 rounded-full text-m font-medium transition duration-200 ${selectedIngredients.includes(ingredient)
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                      }`}
                  >
                    {ingredient}
                    {selectedIngredients.includes(ingredient) && (
                      <X size={14} className="inline-block ml-1" />
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Courses Section */}
          <div className="mb-8">
            <button
              className="flex items-center justify-between w-full p-3 bg-gray-300 rounded-lg text-lg font-semibold text-white-700 hover:bg-gray-200 transition duration-200"
              onClick={() => toggleSection('courses')}
            >
              <span>Courses</span>
              {expandedSections.courses ? <ChevronUp size={24} /> : <ChevronDown size={24} />}
            </button>
            {expandedSections.courses && (
              <div className="mt-4 p-0 grid grid-cols-2 md:grid-cols-3 gap-2">
                {courses.map(course => (
                  <label key={course} className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="radio"
                      checked={selectedCourse === course}
                      onChange={() => handleCourseChange(course)}
                      className="form-radio h-5 w-5 text-blue-500 focus:ring-blue-400"
                    />
                    <span className="text-gray-700">{course}</span>
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Cravings Section */}
          <div className="mb-8">
            <button
              className="flex items-center justify-between w-full p-3 bg-gray-300 rounded-lg text-lg font-semibold text-white-700 hover:bg-gray-200 transition duration-200"
              onClick={() => toggleSection('cravings')}
            >
              <span>Cravings</span>
              {expandedSections.cravings ? <ChevronUp size={24} /> : <ChevronDown size={24} />}
            </button>
            {expandedSections.cravings && (
              <div className="mt-4 p-5 flex gap-4">
                {cravings.map(craving => (
                  <label key={craving} className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedCravings.includes(craving)}
                      onChange={() => handleCravingChange(craving)}
                      className="form-checkbox h-5 w-5 text-blue-500 rounded focus:ring-blue-400"
                    />
                    <span className="text-gray-700">{craving}</span>
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Submit Button */}
          <button className="w-1/2 bg-gray-800 text-white py-3 px-4 rounded-full text-lg font-semibold hover:bg-gray-700 transition duration-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-opacity-50">
            Find Recipes
          </button>
        </div>

        <div className="result w-2/3 h-screen bg-white-200">
          <h1 className="text-3xl p-3 t-0 font-bold mb-6 text-center">Top Recommendation</h1>
            
            {exampleRecipes.map((recipe, index) => (
              <RecipeCard
                key={index}
                title={recipe.title}
                description={recipe.description}
                cookTime={recipe.cookTime}
                servings={recipe.servings}
                difficulty={recipe.difficulty}
                image={recipe.image}
              />
            ))}

        </div>
      </div>

    </>
  );
};

export default Home;