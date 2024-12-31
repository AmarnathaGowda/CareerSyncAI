// src/components/FileUpload.jsx
import React, { useState } from 'react';

const API_URL = process.env.REACT_APP_API_URL;

export function FileUpload({ setResults }) {
 const [file, setFile] = useState(null);
 const [jobDescription, setJobDescription] = useState('');
 const [loading, setLoading] = useState(false);
 const [error, setError] = useState('');

 const handleSubmit = async (e) => {
   e.preventDefault();
   
   if (!file) {
     setError('Please select a resume file');
     return;
   }

   setLoading(true);
   setError('');

   const formData = new FormData();
   formData.append('resume', file);
   formData.append('job_description', jobDescription);

   try {
     const response = await fetch(`${API_URL}/analyze`, {
       method: 'POST',
       body: formData,
     });

     if (!response.ok) {
       throw new Error(`HTTP error! status: ${response.status}`);
     }

     const data = await response.json();
     
     if (data.status === 'success') {
       setResults(data.analysis);
       setFile(null);
       setJobDescription('');
     } else {
       setError(data.error || 'Analysis failed. Please try again.');
     }
   } catch (err) {
     console.error('Error:', err);
     setError('Failed to analyze resume. Please try again.');
   } finally {
     setLoading(false);
   }
 };

 return (
   <div className="max-w-2xl mx-auto bg-white rounded-lg shadow-lg p-6 mb-8">
     <h2 className="text-xl font-bold mb-6">Resume Analysis</h2>
     
     <form onSubmit={handleSubmit} className="space-y-6">
       <div>
         <label className="block text-sm font-medium text-gray-700 mb-2">
           Upload Resume (PDF)
         </label>
         <input
           type="file"
           accept=".pdf"
           onChange={(e) => setFile(e.target.files[0])}
           className="w-full border border-gray-300 rounded-md p-2 
                    focus:outline-none focus:ring-2 focus:ring-blue-500"
           required
         />
         {file && (
           <p className="mt-1 text-sm text-gray-500">
             Selected file: {file.name}
           </p>
         )}
       </div>

       <div>
         <label className="block text-sm font-medium text-gray-700 mb-2">
           Job Description
         </label>
         <textarea
           value={jobDescription}
           onChange={(e) => setJobDescription(e.target.value)}
           className="w-full border border-gray-300 rounded-md p-3 h-32
                    focus:outline-none focus:ring-2 focus:ring-blue-500"
           placeholder="Paste the job description here..."
           required
         />
       </div>

       {error && (
         <div className="bg-red-50 border-l-4 border-red-500 p-4">
           <p className="text-red-700">{error}</p>
         </div>
       )}

       <button
         type="submit"
         disabled={loading}
         className="w-full bg-blue-600 text-white px-6 py-3 rounded-md
                  hover:bg-blue-700 focus:outline-none focus:ring-2 
                  focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50
                  disabled:cursor-not-allowed transition-colors duration-200"
       >
         {loading ? (
           <span className="flex items-center justify-center">
             <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
               <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
               <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
             </svg>
             Analyzing...
           </span>
         ) : (
           'Analyze Resume'
         )}
       </button>
     </form>
   </div>
 );
}