export function ScoreCard({ title, score }) {
    return (
      <div className="bg-gray-50 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-gray-600">{title}</h3>
        <div className="text-3xl font-bold text-blue-600">{score}%</div>
      </div>
    );
  }