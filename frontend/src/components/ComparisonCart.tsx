import { useState } from 'react';
import { useAppStore } from '../store/useAppStore';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { useNavigate } from 'react-router-dom';

export function ComparisonCart() {
  const [isExpanded, setIsExpanded] = useState(false);
  const { comparisonCart, removeFromComparison, clearComparison } = useAppStore();
  const navigate = useNavigate();

  const handleCompare = () => {
    if (comparisonCart.length >= 2) {
      navigate('/compare');
      setIsExpanded(false);
    }
  };

  if (comparisonCart.length === 0) {
    return null;
  }

  return (
    <div className="fixed bottom-6 right-6 z-40">
      {/* Floating Button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="relative bg-blue-600 hover:bg-blue-700 text-white rounded-full p-4 shadow-lg transition-all duration-200 hover:scale-110"
      >
        <svg
          className="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
          />
        </svg>
        <div className="absolute -top-1 -right-1">
          <Badge variant="danger" size="sm">
            {comparisonCart.length}
          </Badge>
        </div>
      </button>

      {/* Expanded Panel */}
      {isExpanded && (
        <div className="absolute bottom-20 right-0 bg-white rounded-lg shadow-xl border border-gray-200 w-96 max-h-[500px] flex flex-col">
          {/* Header */}
          <div className="p-4 border-b border-gray-200 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">
              Comparison Cart
            </h3>
            <button
              onClick={() => setIsExpanded(false)}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Lap List */}
          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {comparisonCart.map((item, index) => (
              <div
                key={`${item.videoName}-${item.lapNumber}`}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {item.videoName}
                  </p>
                  <p className="text-xs text-gray-600">
                    Lap {item.lapNumber}
                    {item.lapTime && ` - ${item.lapTime}`}
                  </p>
                </div>
                <button
                  onClick={() => removeFromComparison(item.videoName, item.lapNumber)}
                  className="ml-2 text-red-500 hover:text-red-700 p-1"
                  title="Remove from comparison"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ))}
          </div>

          {/* Footer Actions */}
          <div className="p-4 border-t border-gray-200 space-y-2">
            <Button
              onClick={handleCompare}
              disabled={comparisonCart.length < 2}
              className="w-full"
            >
              Compare Laps ({comparisonCart.length})
            </Button>
            <button
              onClick={clearComparison}
              className="w-full px-4 py-2 text-sm text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
            >
              Clear All
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
