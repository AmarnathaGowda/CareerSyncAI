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

app = Flask(__name__)

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
    'matching_skills': fields.List(fields.String, example=['python', 'javascript']),
    'missing_skills': fields.List(fields.String, example=['docker']),
    'recommendation': fields.String(example='Strong Match'),
    'skill_categories': fields.Raw(description='Categorized skills')
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
        
        # Load skills data from JSON file
        with open('skills_data.json', 'r') as f:
            skills_data = json.load(f)
            
        self.skill_patterns = skills_data['skill_patterns']
        self.skill_weights = skills_data['skill_weights']
        self.exclude_words = set(skills_data['exclude_words'])
        
        # Create flattened skill list
        self.valid_skills = set([
            skill.lower() 
            for category in self.skill_patterns.values() 
            for skill in category
        ])

    def preprocess_text(self, text):
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        doc = self.nlp(text)
        return ' '.join([token.lemma_ for token in doc if not token.is_stop])

    def extract_skills(self, text):
        doc = self.nlp(text.lower())
        potential_skills = set()
        categorized_skills = {category: [] for category in self.skill_patterns.keys()}
        
        # Process noun chunks
        for chunk in doc.noun_chunks:
            cleaned_chunk = chunk.text.strip()
            if any(skill in cleaned_chunk for skill in self.valid_skills):
                potential_skills.add(cleaned_chunk)
        
        # Process individual tokens
        for token in doc:
            if token.text in self.valid_skills and token.text not in self.exclude_words:
                potential_skills.add(token.text)
        
        # Validate and categorize skills
        validated_skills = []
        for skill in potential_skills:
            for category, patterns in self.skill_patterns.items():
                if any(pattern in skill for pattern in patterns):
                    validated_skills.append(skill)
                    categorized_skills[category].append(skill)
                    break
        
        return list(set(validated_skills)), categorized_skills

    def calculate_similarity(self, resume_text, job_description):
        processed_resume = self.preprocess_text(resume_text)
        processed_job = self.preprocess_text(job_description)
        
        # Extract and categorize skills
        resume_skills, resume_categorized = self.extract_skills(resume_text)
        job_skills, job_categorized = self.extract_skills(job_description)
        
        resume_skills = set(resume_skills)
        job_skills = set(job_skills)
        
        # Calculate weighted skill match
        matching_skills = resume_skills.intersection(job_skills)
        total_weight = 0
        matched_weight = 0
        
        for category, skills in job_categorized.items():
            category_weight = self.skill_weights.get(category, 1.0)
            for skill in skills:
                total_weight += category_weight
                if skill in matching_skills:
                    matched_weight += category_weight
        
        skill_match_percentage = matched_weight / total_weight if total_weight > 0 else 0
        
        # Calculate text similarity
        tfidf_matrix = self.vectorizer.fit_transform([processed_resume, processed_job])
        text_similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        
        # Combine scores
        final_score = (text_similarity * 0.4) + (skill_match_percentage * 0.6)
        
        return {
            'similarity_score': final_score,
            'skill_match_percentage': skill_match_percentage,
            'matching_skills': list(matching_skills),
            'missing_skills': list(job_skills - resume_skills),
            'categorized_skills': {
                'resume': resume_categorized,
                'job': job_categorized
            }
        }

    def analyze_match(self, resume_text, job_description):
        results = self.calculate_similarity(resume_text, job_description)
        
        return {
            'overall_match': round(results['similarity_score'] * 100, 2),
            'skill_match': round(results['skill_match_percentage'] * 100, 2),
            'matching_skills': results['matching_skills'],
            'missing_skills': results['missing_skills'],
            'skill_categories': results['categorized_skills'],
            'recommendation': self._generate_recommendation(results)
        }
    
    def _generate_recommendation(self, results):
        score = results['similarity_score']
        if score >= 0.7:
            return "Strong Match: Your profile aligns well with the job requirements"
        elif score >= 0.5:
            return "Moderate Match: Consider emphasizing relevant skills and experience"
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
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], 
                               f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
        
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