
import { useState, useEffect } from 'react';
import { FaArrowUp } from 'react-icons/fa';

export default function ScrollToTop() {
  const [isVisible, setIsVisible] = useState(false);

  const toggleVisibility = () => {
    const mainElement = document.querySelector('main');
    if (mainElement && mainElement.scrollTop > 300) {
      setIsVisible(true);
    } else {
      setIsVisible(false);
    }
  };

  const scrollToTop = () => {
    const mainElement = document.querySelector('main');
    if (mainElement) {
      mainElement.scrollTo({
        top: 0,
        behavior: 'smooth',
      });
    }
  };

  useEffect(() => {
    const mainElement = document.querySelector('main');
    if (mainElement) {
      mainElement.addEventListener('scroll', toggleVisibility);
      return () => {
        mainElement.removeEventListener('scroll', toggleVisibility);
      };
    }
  }, []);

  return (
    <>
      {isVisible && (
        <button
          onClick={scrollToTop}
          className="fixed bottom-8 right-8 p-3 bg-primary-600 hover:bg-primary-700 dark:hover:bg-primary-500 text-white rounded-full shadow-lg transition-all duration-200 hover:scale-110 z-50"
          title="Ir arriba"
          aria-label="Ir arriba"
        >
          <FaArrowUp className="w-5 h-5" />
        </button>
      )}
    </>
  );
}
