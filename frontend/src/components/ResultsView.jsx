import { ScoreCard } from './ScoreCard';

function SkillsList({ title, skills, type }) {
  const bgColor = type === 'success' ? 'bg-green-50' : 'bg-yellow-50';
  const textColor = type === 'success' ? 'text-green-600' : 'text-yellow-600';

  return (
    <div>
      <h3 className="font-bold mb-2">{title}</h3>
      <div className={`${bgColor} rounded-lg p-4`}>
        <ul className="space-y-1">
          {skills.map((skill, index) => (
            <li key={index} className={`${textColor}`}>
              • {skill}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export function ResultsView({ results }) {
  return (
    <div className="max-w-4xl mx-auto bg-white rounded-lg shadow p-6">
      <div className="mb-6">
        <h2 className="text-xl font-bold mb-4">Match Analysis</h2>
        <div className="grid grid-cols-2 gap-4">
          <ScoreCard title="Overall Match" score={results.overall_match} />
          <ScoreCard title="Skill Match" score={results.skill_match} />
        </div>
      </div>

      <div className="mb-6">
        <h3 className="font-bold mb-2">Recommendation</h3>
        <p className="p-3 bg-blue-50 rounded">{results.recommendation}</p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
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
    </div>
  );
}