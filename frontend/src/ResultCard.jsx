import React from 'react';

// A helper component for displaying individual data points
const InfoPill = ({ label, value, className = '' }) => (
  <div className={`bg-gray-100/80 rounded-full px-4 py-2 text-sm ${className}`}>
    <span className="font-semibold text-gray-800">{label}:</span>
    <span className="ml-2 text-gray-600">{value}</span>
  </div>
);

// A helper to format price values
const formatPrice = (price) => {
    if (price === null || price === undefined) return 'N/A';
    return `$${Number(price).toLocaleString()}`;
}

function ResultCard({ result }) {
  // Destructure the data for easier access
  const { gptData, valuationData, dealRatingData } = result;

  // Determine the color of the deal rating badge
  const getRatingColor = (rating) => {
    const lowerRating = rating?.toLowerCase();
    if (lowerRating?.includes('great') || lowerRating?.includes('good')) {
      return 'bg-green-100 text-green-800 border-green-200';
    }
    if (lowerRating?.includes('fair')) {
      return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    }
    return 'bg-red-100 text-red-800 border-red-200';
  };

  return (
    <div className="bg-white/80 backdrop-blur-lg rounded-3xl shadow-lg ring-1 ring-black/5 p-6 md:p-8">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

        {/* Left Column: Vehicle Info */}
        <div className="md:col-span-2 space-y-4">
          <h2 className="text-2xl font-bold text-gray-900">
            {gptData.year} {gptData.make} {gptData.model}
          </h2>
          <p className="text-gray-600 text-base">
            {gptData.description || "No description available."}
          </p>
          <div className="flex flex-wrap gap-3 pt-2">
            <InfoPill label="Listing Price" value={formatPrice(gptData.price)} />
            <InfoPill label="Mileage" value={gptData.mileage ? `${Number(gptData.mileage).toLocaleString()} miles` : 'N/A'} />
          </div>
        </div>

        {/* Right Column: Deal Rating */}
        <div className="flex flex-col items-center justify-center bg-gray-50/70 rounded-2xl p-4 space-y-2 border">
          <h3 className="text-lg font-semibold text-gray-800">Deal Rating</h3>
          <span className={`px-4 py-1.5 rounded-full text-lg font-bold ${getRatingColor(dealRatingData?.rating)}`}>
            {dealRatingData?.rating || 'N/A'}
          </span>
          <p className="text-sm text-gray-600 text-center">
            Market Average: {formatPrice(valuationData?.mean)}
          </p>
        </div>
      </div>
    </div>
  );
}

export default ResultCard;