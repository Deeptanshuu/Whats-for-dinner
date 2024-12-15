import React, { useState } from 'react';

const VegToggle = ({ initialState = false, onChange }) => {
  const [isVeg, setIsVeg] = useState(initialState);

  const handleToggle = () => {
    const newState = !isVeg;
    setIsVeg(newState);
    if (onChange) {
      onChange(newState);
    }
  };

  return (
    <button
      onClick={handleToggle}
      className={`relative inline-flex items-center ring-2 ring-offset-2   h-6 rounded-full w-11 focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors ease-in-out duration-200 ${
        isVeg ? 'bg-green-500 ring-green-500' : 'bg-stone-400 ring-stone-500 focus:ring-green-500'
      }`}
    >
      <span className="sr-only">Toggle vegetarian</span>
      <span
        className={`inline-block w-4 h-4 transform rounded-full bg-white transition ease-in-out duration-200 ${
          isVeg ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  );
};

export default VegToggle;