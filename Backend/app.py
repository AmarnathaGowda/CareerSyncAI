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
import json
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

api = Api(
    app,
    version='1.0',
    title='CareerSync AI',
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
    'matching_skills': fields.List(fields.String),
    'missing_skills': fields.List(fields.String),
    'recommendation': fields.String(),
    'categorized_skills': fields.Raw(description='Skills by category')
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
        
        with open('skills_data.json', 'r') as f:
            skills_data = json.load(f)
        
        self.skill_patterns = skills_data['skill_patterns']
        self.skill_weights = skills_data['skill_weights']
        self.exclude_words = set(skills_data['exclude_words'])
        
        # Create exact skill matches dictionary
        self.valid_skills = {}
        for category, skills in self.skill_patterns.items():
            for skill in skills:
                self.valid_skills[skill.lower()] = category

    def clean_text(self, text):
        """Clean text by removing special characters and normalizing whitespace"""
        text = re.sub(r'[^\w\s-]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n', ' ', text)
        return text.lower().strip()

    def is_date_or_location(self, text):
        """Check if text contains date or location patterns"""
        date_patterns = [
            r'\d{4}\s*-\s*\d{4}',
            r'\d{4}\s*-\s*present',
            r'(january|february|march|april|may|june|july|august|september|october|november|december)',
            r'\d{1,2}\s*years?',
            r'\d{4}'
        ]
        
        location_patterns = [
            r'\b(india|usa|uk|canada|australia)\b',
            r'\b[a-z]+\s*,\s*[a-z]+\b'
        ]
        
        return any(re.search(pattern, text, re.IGNORECASE) 
                  for pattern in date_patterns + location_patterns)

    def extract_skills(self, text):
        """Extract skills with improved accuracy"""
        text = self.clean_text(text)
        doc = self.nlp(text)
        
        extracted_skills = {category: set() for category in self.skill_patterns.keys()}
        
        # Process text in chunks
        chunks = list(doc.noun_chunks) + [token for token in doc 
                                        if token.pos_ in ['PROPN', 'NOUN']]
        
        for chunk in chunks:
            chunk_text = str(chunk).lower()
            
            # Skip if chunk contains date, location or excluded words
            if (self.is_date_or_location(chunk_text) or 
                any(word in chunk_text for word in self.exclude_words)):
                continue
            
            # Check for exact matches
            if chunk_text in self.valid_skills:
                category = self.valid_skills[chunk_text]
                extracted_skills[category].add(chunk_text)
                continue
            
            # Check for compound skills
            for skill, category in self.valid_skills.items():
                if (len(skill.split()) > 1 and 
                    skill in chunk_text and 
                    len(chunk_text.split()) <= len(skill.split()) + 1):
                    extracted_skills[category].add(skill)
        
        return {category: list(skills) for category, skills in extracted_skills.items()}

    def calculate_similarity(self, resume_text, job_description):
        """Calculate similarity with improved skill weighting"""
        resume_skills = self.extract_skills(resume_text)
        job_skills = self.extract_skills(job_description)
        
        # Flatten skills
        resume_flat = set([skill for skills in resume_skills.values() 
                          for skill in skills])
        job_flat = set([skill for skills in job_skills.values() 
                       for skill in skills])
        
        # Calculate weighted match
        total_weight = 0
        matched_weight = 0
        
        for category, skills in job_skills.items():
            weight = self.skill_weights.get(category, 1.0)
            for skill in skills:
                total_weight += weight
                if skill in resume_flat:
                    matched_weight += weight
        
        skill_match_percentage = (matched_weight / total_weight 
                                if total_weight > 0 else 0)
        
        # Calculate text similarity
        processed_resume = self.clean_text(resume_text)
        processed_job = self.clean_text(job_description)
        
        tfidf_matrix = self.vectorizer.fit_transform([processed_resume, processed_job])
        text_similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        
        # Combined score
        final_score = (text_similarity * 0.4) + (skill_match_percentage * 0.6)
        
        return {
            'similarity_score': final_score,
            'skill_match_percentage': skill_match_percentage,
            'matching_skills': list(resume_flat.intersection(job_flat)),
            'missing_skills': list(job_flat - resume_flat),
            'categorized_skills': {
                'resume': resume_skills,
                'job': job_skills
            }
        }

    def analyze_match(self, resume_text, job_description):
        """Generate final analysis"""
        results = self.calculate_similarity(resume_text, job_description)
        
        return {
            'overall_match': round(results['similarity_score'] * 100, 2),
            'skill_match': round(results['skill_match_percentage'] * 100, 2),
            'matching_skills': results['matching_skills'],
            'missing_skills': results['missing_skills'],
            'categorized_skills': results['categorized_skills'],
            'recommendation': self._generate_recommendation(results)
        }
    
    def _generate_recommendation(self, results):
        """Generate recommendation based on match score"""
        score = results['similarity_score']
        if score >= 0.7:
            return "Strong Match: Profile aligns well with requirements"
        elif score >= 0.5:
            return "Moderate Match: Consider emphasizing relevant skills"
        return "Limited Match: Significant skill gaps identified"

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
        temp_path = os.path.join(
            app.config['UPLOAD_FOLDER'],
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        )
        
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
