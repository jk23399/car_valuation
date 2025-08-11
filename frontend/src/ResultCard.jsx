import React from 'react';

// Small pill for key/value facts
const InfoPill = ({ label, value, className = '' }) => (
  <div className={`bg-gray-100/80 rounded-full px-4 py-2 text-sm ${className}`}>
    <span className="font-semibold text-gray-800">{label}:</span>
    <span className="ml-2 text-gray-600">{value}</span>
  </div>
);

// Price formatter
const formatPrice = (price) => {
  if (price === null || price === undefined) return 'N/A';
  return `$${Number(price).toLocaleString()}`;
};

// Simple alert banner
const FlagBanner = ({ level = 'red', children }) => {
  const styles = {
    red: 'bg-red-50 border-red-300 text-red-800',
    yellow: 'bg-yellow-50 border-yellow-300 text-yellow-800',
    green: 'bg-green-50 border-green-300 text-green-800',
  }[level] || 'bg-gray-50 border-gray-300 text-gray-800';

  return (
    <div className={`w-full border rounded-xl px-4 py-3 text-sm font-medium ${styles}`}>
      {children}
    </div>
  );
};

function ResultCard({ result }) {
  // Pull data and flags (backend) with a local fallback
  const { gptData, valuationData, dealRatingData, flags: serverFlags = [] } = result || {};
  const vin = gptData?.vin ? String(gptData.vin).trim() : '';
  const vinMissing = vin.length !== 17;

  // Merge server-provided flags with local VIN-missing detection
  const flags = [...serverFlags];
  if (vinMissing && !flags.some(f => f?.code === 'VIN_MISSING')) {
    flags.push({
      code: 'VIN_MISSING',
      level: 'red',
      label: 'Red flag',
      message:
        'VIN is missing in the listing. Ask the seller for a clear VIN photo (windshield/driver-door sticker) before meeting.',
    });
  }

  // Normalize rating to 4 buckets
  const normalizeRating = (r) => {
    const s = (r || '').toLowerCase();
    if (s.includes('excellent')) return 'Excellent Deal';
    if (s.includes('good'))      return 'Good Deal';
    if (s.includes('fair'))      return 'Fair Deal';   // "Fair Price" → "Fair Deal"
    return 'Bad Deal';                                  // "Overpriced" → "Bad Deal"
  };

  // Badge styles
  const getRatingStyle = (label) => {
    switch (label) {
      case 'Excellent Deal': return 'bg-green-600 text-white border border-green-700';
      case 'Good Deal':      return 'bg-green-200 text-green-900 border border-green-300';
      case 'Fair Deal':      return 'bg-yellow-200 text-yellow-900 border border-yellow-300';
      default:               return 'bg-red-600 text-white border border-red-700';
    }
  };

  const maker = gptData?.maker || gptData?.make || '';
  const model = gptData?.model || '';
  const year  = gptData?.year || '';

  const fairPrice = valuationData?.valuation_price;
  const low  = valuationData?.range?.low;
  const high = valuationData?.range?.high;
  const region = valuationData?.adjust_detail?.regionName;
  const base   = valuationData?.adjust_detail?.base_price;

  const normalized = normalizeRating(dealRatingData?.rating);

  return (
    <div className="bg-white/80 backdrop-blur-lg rounded-3xl shadow-lg ring-1 ring-black/5 p-6 md:p-8">
      {/* Risk flags banner */}
      {flags.length > 0 && (
        <div className="mb-4 space-y-2">
          {flags.map((f, i) => (
            <FlagBanner key={i} level={f.level}>
              <span className="mr-2 inline-block rounded-full bg-red-600 text-white px-2 py-0.5 text-xs font-bold">
                {f.label || 'Red flag'}
              </span>
              {f.message || 'Potential risk detected.'}
            </FlagBanner>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Left: Vehicle info */}
        <div className="md:col-span-2 space-y-4">
          <h2 className="text-2xl font-bold text-gray-900">
            {year} {maker} {model}
          </h2>
          <p className="text-gray-600 text-base">
            {gptData?.description || 'No description available.'}
          </p>
          <div className="flex flex-wrap gap-3 pt-2">
            <InfoPill label="Listing Price" value={formatPrice(gptData?.price)} />
            <InfoPill
              label="Mileage"
              value={gptData?.mileage ? `${Number(gptData.mileage).toLocaleString()} miles` : 'N/A'}
            />
            {region && <InfoPill label="Region" value={region} />}
          </div>
        </div>

        {/* Right: Deal Rating */}
        <div className="flex flex-col items-center justify-center bg-gray-50/70 rounded-2xl p-4 space-y-2 border">
          <h3 className="text-lg font-semibold text-gray-800">Deal Rating</h3>
          <span className={`px-4 py-1.5 rounded-full text-lg font-bold ${getRatingStyle(normalized)}`}>
            {normalized}
          </span>

          <p className="text-sm text-gray-600 text-center">
            Fair Price: {formatPrice(fairPrice)}
          </p>

          {low !== undefined && high !== undefined && (
            <p className="text-xs text-gray-500 text-center">
              Range: {formatPrice(low)} – {formatPrice(high)}
            </p>
          )}

          {base !== undefined && (
            <p className="text-xs text-gray-400 text-center">
              CIS Baseline: {formatPrice(base)}
            </p>
          )}

          {dealRatingData?.comment && (
            <p className="text-xs text-gray-500 text-center mt-1">{dealRatingData.comment}</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default ResultCard;
