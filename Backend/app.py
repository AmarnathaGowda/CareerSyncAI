from flask import Flask, request
from flask_restx import Api, Resource, fields
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
import os
import spacy
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import PyPDF2
import tempfile
from datetime import datetime

app = Flask(__name__)

api = Api(
    app,
    version='1.0',
    title='CareerSync AI API',
    description='AI-powered resume and job description matching API',
    doc='/swagger'
)

ns = api.namespace('api/v1', description='Resume matching operations')

UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

analysis_model = api.model('Analysis', {
    'overall_match': fields.Float(example=75.5),
    'skill_match': fields.Float(example=80.0),
    'matching_skills': fields.List(fields.String, example=['python', 'javascript']),
    'missing_skills': fields.List(fields.String, example=['docker']),
    'recommendation': fields.String(example='Strong Match')
})

response_model = api.model('Response', {
    'status': fields.String(example='success'),
    'timestamp': fields.DateTime(),
    'analysis': fields.Nested(analysis_model)
})

class ResumeJobMatcher:
    def __init__(self):
        self.nlp = spacy.load('en_core_web_sm')
        self.vectorizer = TfidfVectorizer(stop_words='english')
        
    def preprocess_text(self, text):
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        doc = self.nlp(text)
        return ' '.join([token.lemma_ for token in doc if not token.is_stop])
    
    def extract_skills(self, text):
        doc = self.nlp(text.lower())
        skills = []
        for chunk in doc.noun_chunks:
            skills.append(chunk.text)
        for token in doc:
            if token.pos_ in ['PROPN', 'NOUN']:
                skills.append(token.text)
        return list(set(skills))
    
    def calculate_similarity(self, resume_text, job_description):
        processed_resume = self.preprocess_text(resume_text)
        processed_job = self.preprocess_text(job_description)
        
        tfidf_matrix = self.vectorizer.fit_transform([processed_resume, processed_job])
        similarity_score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        
        resume_skills = set(self.extract_skills(resume_text))
        job_skills = set(self.extract_skills(job_description))
        
        matching_skills = resume_skills.intersection(job_skills)
        skill_match_percentage = len(matching_skills) / len(job_skills) if job_skills else 0
        
        return {
            'similarity_score': similarity_score,
            'skill_match_percentage': skill_match_percentage,
            'matching_skills': list(matching_skills),
            'missing_skills': list(job_skills - resume_skills)
        }
    
    def analyze_match(self, resume_text, job_description):
        results = self.calculate_similarity(resume_text, job_description)
        return {
            'overall_match': round(results['similarity_score'] * 100, 2),
            'skill_match': round(results['skill_match_percentage'] * 100, 2),
            'matching_skills': results['matching_skills'],
            'missing_skills': results['missing_skills'],
            'recommendation': self._generate_recommendation(results)
        }
    
    def _generate_recommendation(self, results):
        if results['similarity_score'] >= 0.7:
            return "Strong Match: Well-aligned with requirements"
        elif results['similarity_score'] >= 0.5:
            return "Moderate Match: Consider highlighting relevant skills"
        return "Weak Match: Significant gaps exist"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(pdf_file_path):
    text = ""
    with open(pdf_file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
    return text

matcher = ResumeJobMatcher()

upload_parser = api.parser()
upload_parser.add_argument('resume', type=FileStorage, location='files', required=True)
upload_parser.add_argument('job_description', type=str, location='form', required=True)

@ns.route('/analyze')
class ResumeAnalyzer(Resource):
    @api.expect(upload_parser)
    @api.response(200, 'Success', response_model)
    def post(self):
        args = upload_parser.parse_args()
        resume_file = args['resume']
        job_description = args['job_description']
        
        if not resume_file or resume_file.filename == '':
            api.abort(400, 'No resume file provided')
            
        if not allowed_file(resume_file.filename):
            api.abort(400, 'Only PDF files allowed')
        
        filename = secure_filename(resume_file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
        
        try:
            resume_file.save(temp_path)
            resume_text = extract_text_from_pdf(temp_path)
            analysis = matcher.analyze_match(resume_text, job_description)
            
            return {
                'status': 'success',
                'timestamp': datetime.now().isoformat(),
                'analysis': analysis
            }, 200
            
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

if __name__ == '__main__':
    app.run(debug=True, port=5000)