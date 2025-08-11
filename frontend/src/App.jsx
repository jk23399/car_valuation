import { useState, useRef } from 'react';
import ResultCard from './ResultCard';

function App() {
  const [url, setUrl] = useState('');
  const [image, setImage] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const imageInputRef = useRef(null);

  // Handler for URL input changes
  const handleUrlChange = (event) => {
    setUrl(event.target.value);
    // Clear image state if user starts typing a URL
    if (image) {
      setImage(null);
      if (imageInputRef.current) {
        // Corrected the typo here
        imageInputRef.current.value = null; // Reset the file input visually
      }
    }
  };

  // Handler for image file selection
  const handleImageChange = (event) => {
    setUrl(''); // Clear URL if user uploads an image
    const file = event.target.files?.[0];
    if (file) setImage(file);
  };

  // Handler for drag-and-drop image functionality
  const handleImageDrop = (event) => {
    event.preventDefault();
    setUrl(''); // Clear URL
    const file = event.dataTransfer.files?.[0];
    if (file) {
      setImage(file);
      // Synchronize the dropped file with the hidden file input
      if (imageInputRef.current) {
        imageInputRef.current.files = event.dataTransfer.files;
      }
    }
  };

  // Prevent default behavior when dragging over the drop zone
  const handleDragOver = (event) => event.preventDefault();

  // Main function to handle the API call
  const handleEvaluate = async () => {
    setIsLoading(true);
    setResult(null);
    setError(null);

    try {
      let response;
      // Case 1: User provided a URL
      if (url) {
        // Use the relative path to leverage the Vite proxy
        response = await fetch('/api/evaluate', {
          method: 'POST',
          headers: {
            // Set the correct Content-Type for JSON data
            'Content-Type': 'application/json',
          },
          // Send the URL in a JSON object
          body: JSON.stringify({ url: url }),
        });
      } 
      // Case 2: User provided an image
      else if (image) {
        const formData = new FormData();
        formData.append('image', image);

        // IMPORTANT: This requires a separate backend endpoint that can handle image uploads.
        // The browser sets the 'Content-Type' for FormData automatically.
        response = await fetch('/api/evaluate_image', {
          method: 'POST',
          body: formData,
        });
      } 
      // Case 3: No input provided
      else {
        throw new Error("Please provide a URL or an image.");
      }

      const data = await response.json();

      // Check if the server responded with an error status
      if (!response.ok) {
        throw new Error(data.error || `Request failed with status ${response.status}`);
      }
      setResult(data);
    } catch (err) {
      // Ensure the error message is always a string
      setError(err.message || 'An unknown error occurred.');
    } finally {
      setIsLoading(false);
    }
  };

  // Trigger the hidden file input when the upload button is clicked
  const handleImageUploadClick = () => imageInputRef.current?.click();

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#ffd7dc] via-[#ffe6c6] to-[#cfe5ff] flex items-center justify-center px-4 font-sans">
      <div className="w-full max-w-4xl text-center">
        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-gray-900 drop-shadow-sm">
         AI Car Deal Grader
        </h1>
        <p className="mt-4 text-gray-700/80">
        Evaluate car listings using an LLM + Vehicle Pricing API. Enter a Craigslist URL or upload an image.
        </p>

        <section className="mt-10 rounded-3xl bg-white/70 backdrop-blur-md shadow-lg ring-1 ring-black/5 p-5 md:p-7">
          <div className="flex flex-col md:flex-row gap-3 md:gap-4 items-stretch">
            <div className="flex-1">
              <label htmlFor="url" className="sr-only">Craigslist URL</label>
              <div className="rounded-full border border-gray-200 bg-white px-5 py-3 shadow-sm focus-within:ring-2 focus-within:ring-indigo-300 transition-shadow">
                <input
                  type="url"
                  id="url"
                  placeholder="https://phoenix.craigslist.org/..."
                  value={url}
                  onChange={handleUrlChange}
                  disabled={isLoading}
                  className="w-full bg-transparent outline-none text-gray-900 placeholder:text-gray-400"
                />
              </div>
            </div>

            <div className="md:w-72">
              <button
                type="button"
                onClick={handleImageUploadClick}
                onDragOver={handleDragOver}
                onDrop={handleImageDrop}
                className="w-full h-full rounded-full border border-dashed border-gray-300 bg-white px-5 py-3 text-gray-700 shadow-sm hover:border-indigo-300 hover:bg-indigo-50/40 transition disabled:opacity-60 truncate"
                disabled={isLoading}
                title={image ? image.name : "Drag & drop or click to upload"}
              >
                {image ? image.name : 'Upload image'}
              </button>
              <input
                id="image"
                type="file"
                accept="image/*"
                className="hidden"
                ref={imageInputRef}
                onChange={handleImageChange}
                disabled={isLoading}
              />
            </div>

            <button
              type="button"
              onClick={handleEvaluate}
              disabled={isLoading || (!url && !image)}
              className="rounded-full px-6 py-3 font-semibold bg-indigo-600 text-white shadow-md hover:bg-indigo-500 active:scale-[0.99] transition disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Evaluating…' : 'Evaluate'}
            </button>
          </div>

          {error && <div className="mt-4 text-sm font-medium text-red-600 bg-red-100/50 border border-red-200 rounded-lg p-2">{error}</div>}
        </section>

        {isLoading && (
            <div className="mt-8 flex justify-center items-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                <p className="ml-3 text-gray-600">Analyzing, please wait...</p>
            </div>
        )}
        {result && (
          <div className="mt-8 text-left">
            <ResultCard result={result} />
          </div>
        )}
      </div>
    </div>
  );
}

export default App;