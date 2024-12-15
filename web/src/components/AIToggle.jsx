import { useState } from 'react';
import PropTypes from 'prop-types';

const AIToggle = ({ initialState, onChange }) => {
  const [isAI, setIsAI] = useState(initialState);

  const handleToggle = () => {
    const newState = !isAI;
    setIsAI(newState);
    onChange(newState);
  };

  return (
    <div className="flex items-center">
      <span className={`mr-2 text-sm font-medium ${isAI ? 'text-gray-400' : 'text-gray-700'}`}>Brute Force</span>
      <div
        className={`w-14 h-7 flex items-center rounded-full p-1 cursor-pointer transition-colors duration-300 ease-in-out ${
          isAI ? 'bg-blue-600' : 'bg-gray-300'
        }`}
        onClick={handleToggle}
      >
        <div
          className={`bg-white w-5 h-5 rounded-full shadow-md transform transition-transform duration-300 ease-in-out flex items-center justify-center ${
            isAI ? 'translate-x-7' : ''
          }`}
        >
          {isAI && <span className="text-xs">🪄</span>}
        </div>
      </div>
      <span className={`ml-2 text-sm font-medium ${isAI ? 'text-blue-600' : 'text-gray-400'}`}>AI/ML 🪄</span>
    </div>
  );
};

AIToggle.propTypes = {
  initialState: PropTypes.bool.isRequired,
  onChange: PropTypes.func.isRequired,
};

export default AIToggle;
