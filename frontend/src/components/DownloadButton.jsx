export function DownloadButton({ results }) {
    const downloadJSON = () => {
      const element = document.createElement("a");
      const file = new Blob([JSON.stringify(results, null, 2)], {
        type: "application/json"
      });
      element.href = URL.createObjectURL(file);
      element.download = "resume-analysis.json";
      document.body.appendChild(element);
      element.click();
      document.body.removeChild(element);
    };
  
    return (
      <button
        onClick={downloadJSON}
        className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
      >
        Download Analysis
      </button>
    );
  }