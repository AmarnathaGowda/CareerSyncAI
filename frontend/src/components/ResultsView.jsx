
import React from 'react';
import { ScoreCard } from './ScoreCard';
import { DownloadButton } from './DownloadButton';

function SkillsList({ title, skills, type }) {
 const bgColor = type === 'success' ? 'bg-green-50' : 'bg-yellow-50';
 const textColor = type === 'success' ? 'text-green-600' : 'text-yellow-600';
 const borderColor = type === 'success' ? 'border-green-200' : 'border-yellow-200';

 return (
   <div>
     <h3 className="font-bold mb-2">{title}</h3>
     <div className={`${bgColor} rounded-lg p-4 border ${borderColor}`}>
       {skills.length === 0 ? (
         <p className={`${textColor} text-center italic`}>No {title.toLowerCase()} found</p>
       ) : (
         <ul className="space-y-1">
           {skills.map((skill, index) => (
             <li key={index} className={`${textColor} flex items-center`}>
               <span className="mr-2">•</span>
               {skill}
             </li>
           ))}
         </ul>
       )}
     </div>
   </div>
 );
}

export function ResultsView({ results }) {
 const renderSkillCategories = () => {
   const categories = results.categorized_skills?.resume || {};
   return Object.entries(categories).map(([category, skills]) => (
     skills.length > 0 && (
       <div key={category} className="mb-4">
         <h4 className="font-semibold text-gray-700 capitalize mb-2">{category.replace('_', ' ')}</h4>
         <div className="bg-gray-50 p-3 rounded-lg">
           {skills.map((skill, index) => (
             <span key={index} className="inline-block bg-white rounded-full px-3 py-1 text-sm font-semibold text-gray-700 mr-2 mb-2">
               {skill}
             </span>
           ))}
         </div>
       </div>
     )
   ));
 };

 return (
   <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-lg p-6">
     <div className="flex justify-between items-center mb-6">
       <h2 className="text-2xl font-bold text-gray-800">Analysis Results</h2>
       <DownloadButton results={results} />
     </div>

     <div className="grid grid-cols-2 gap-6 mb-8">
       <ScoreCard 
         title="Overall Match" 
         score={results.overall_match}
         description="Match based on skills and content"
       />
       <ScoreCard 
         title="Skill Match" 
         score={results.skill_match}
         description="Direct skill requirement match"
       />
     </div>

     <div className="mb-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
       <h3 className="font-bold text-blue-800 mb-2">Recommendation</h3>
       <p className="text-blue-700">{results.recommendation}</p>
     </div>

     <div className="grid md:grid-cols-2 gap-6 mb-8">
       <SkillsList
         title="Matching Skills"
         skills={results.matching_skills}
         type="success"
       />
       <SkillsList
         title="Missing Skills"
         skills={results.missing_skills}
         type="warning"
       />
     </div>

     <div className="mt-8">
       <h3 className="text-xl font-bold text-gray-800 mb-4">Detailed Skill Analysis</h3>
       <div className="bg-gray-50 rounded-lg p-6">
         {renderSkillCategories()}
       </div>
     </div>
   </div>
 );
}