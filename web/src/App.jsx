import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Home from './components/Home';
import Recipe from './components/Recipe';
import Loading from './components/Loading';
import Footer from './components/Footer';
import WarningHeader from './components/WarningHeader';

function App() {
  return (
    <div className="App">
      <WarningHeader />
      <Router>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/recipe/:id" element={<Recipe />} />
          <Route path="/loading" element={<Loading />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <Footer />
      </Router>
    </div>
  );
}

export default App;
