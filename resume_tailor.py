"""
Smart Resume Tailoring System
Helps students optimize their resumes for specific job postings by analyzing keywords,
required skills, and ATS compatibility to maximize interview chances.
"""

import re
import json
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import Counter
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from enum import Enum

# ============= Data Models =============

class SkillLevel(Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate" 
    ADVANCED = "Advanced"
    EXPERT = "Expert"

@dataclass
class Experience:
    """Work or project experience"""
    title: str
    organization: str
    start_date: str
    end_date: str
    location: str
    bullets: List[str]
    keywords: List[str] = field(default_factory=list)
    
@dataclass
class Education:
    """Education entry"""
    degree: str
    major: str
    school: str
    graduation_date: str
    gpa: Optional[float] = None
    coursework: List[str] = field(default_factory=list)
    
@dataclass
class StudentProfile:
    """Complete student profile"""
    name: str
    email: str
    phone: str
    linkedin: str
    github: Optional[str] = None
    
    education: List[Education] = field(default_factory=list)
    experiences: List[Experience] = field(default_factory=list)
    projects: List[Experience] = field(default_factory=list)
    skills: Dict[str, SkillLevel] = field(default_factory=dict)
    achievements: List[str] = field(default_factory=list)
    
    # Master list of all experiences/bullets
    all_bullets: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class JobPosting:
    """Parsed job posting"""
    title: str
    company: str
    description: str
    requirements: List[str]
    nice_to_have: List[str]
    keywords: List[str]
    skills_required: List[str]
    experience_years: Optional[int] = None
    
@dataclass
class TailoredResume:
    """Optimized resume for specific job"""
    job_title: str
    company: str
    match_score: float
    
    # Selected content
    selected_experiences: List[Experience]
    selected_projects: List[Experience]
    selected_bullets: List[str]
    highlighted_skills: List[str]
    keywords_to_add: List[str]
    
    # Suggestions
    missing_skills: List[str]
    improvement_suggestions: List[str]
    ats_score: float

# ============= Keyword Extractor =============

class KeywordExtractor:
    """Extract and analyze keywords from job postings"""
    
    def __init__(self):
        # Common tech skills to look for
        self.tech_skills = {
            'programming': ['python', 'java', 'javascript', 'c++', 'c#', 'ruby', 'go', 'rust', 'scala', 'kotlin', 'swift', 'php', 'typescript', 'r', 'matlab'],
            'web': ['react', 'angular', 'vue', 'node.js', 'express', 'django', 'flask', 'spring', 'html', 'css', 'sass', 'webpack', 'next.js', 'gatsby'],
            'database': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'cassandra', 'dynamodb', 'firebase', 'elasticsearch'],
            'cloud': ['aws', 'azure', 'gcp', 'google cloud', 'heroku', 'docker', 'kubernetes', 'terraform', 'jenkins', 'ci/cd'],
            'data': ['pandas', 'numpy', 'scikit-learn', 'tensorflow', 'pytorch', 'keras', 'spark', 'hadoop', 'tableau', 'power bi'],
            'tools': ['git', 'github', 'gitlab', 'jira', 'agile', 'scrum', 'linux', 'bash', 'vim', 'vscode']
        }
        
        # Action verbs for bullet points
        self.action_verbs = [
            'developed', 'designed', 'implemented', 'created', 'built', 'established',
            'improved', 'optimized', 'enhanced', 'increased', 'reduced', 'streamlined',
            'led', 'managed', 'coordinated', 'mentored', 'supervised', 'directed',
            'analyzed', 'evaluated', 'researched', 'investigated', 'identified', 'discovered',
            'collaborated', 'partnered', 'contributed', 'participated', 'assisted', 'supported'
        ]
        
        # Soft skills
        self.soft_skills = [
            'leadership', 'communication', 'teamwork', 'problem-solving', 'critical thinking',
            'time management', 'adaptability', 'creativity', 'attention to detail', 'organization'
        ]
    
    def extract_keywords(self, text: str) -> Dict[str, Any]:
        """Extract keywords from job posting"""
        text_lower = text.lower()
        
        # Extract technical skills
        found_tech = {}
        for category, skills in self.tech_skills.items():
            found = [skill for skill in skills if skill in text_lower]
            if found:
                found_tech[category] = found
        
        # Extract soft skills
        found_soft = [skill for skill in self.soft_skills if skill in text_lower]
        
        # Extract years of experience
        experience_pattern = r'(\d+)\+?\s*years?\s*(?:of\s*)?experience'
        exp_match = re.search(experience_pattern, text_lower)
        years = int(exp_match.group(1)) if exp_match else None
        
        # Extract degree requirements
        degree_keywords = ['bachelor', 'master', 'phd', 'doctorate', 'associate']
        degrees = [d for d in degree_keywords if d in text_lower]
        
        # Extract all important words (3+ chars, not common words)
        words = re.findall(r'\b[a-z]{3,}\b', text_lower)
        common_words = {'the', 'and', 'for', 'with', 'you', 'will', 'are', 'our', 'your', 'this', 'that', 'have', 'from'}
        important_words = [w for w in words if w not in common_words]
        word_freq = Counter(important_words).most_common(30)
        
        return {
            'technical_skills': found_tech,
            'soft_skills': found_soft,
            'experience_years': years,
            'degrees': degrees,
            'top_words': [w[0] for w in word_freq],
            'word_frequency': dict(word_freq)
        }
    
    def parse_job_posting(self, posting_text: str, title: str, company: str) -> JobPosting:
        """Parse a job posting into structured format"""
        keywords_data = self.extract_keywords(posting_text)
        
        # Extract requirements vs nice-to-have
        requirements = []
        nice_to_have = []
        
        lines = posting_text.split('\n')
        in_requirements = False
        in_nice = False
        
        for line in lines:
            line_lower = line.lower()
            if any(word in line_lower for word in ['requirement', 'must have', 'required']):
                in_requirements = True
                in_nice = False
            elif any(word in line_lower for word in ['nice to have', 'preferred', 'bonus', 'plus']):
                in_requirements = False
                in_nice = True
            elif line.strip().startswith('•') or line.strip().startswith('-'):
                if in_requirements:
                    requirements.append(line.strip()[1:].strip())
                elif in_nice:
                    nice_to_have.append(line.strip()[1:].strip())
        
        # Flatten technical skills
        all_tech_skills = []
        for skills in keywords_data['technical_skills'].values():
            all_tech_skills.extend(skills)
        
        return JobPosting(
            title=title,
            company=company,
            description=posting_text,
            requirements=requirements,
            nice_to_have=nice_to_have,
            keywords=keywords_data['top_words'],
            skills_required=all_tech_skills + keywords_data['soft_skills'],
            experience_years=keywords_data['experience_years']
        )

# ============= Resume Analyzer =============

class ResumeAnalyzer:
    """Analyze and score resumes against job postings"""
    
    def __init__(self):
        self.keyword_extractor = KeywordExtractor()
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
    def analyze_student_profile(self, profile: StudentProfile) -> Dict[str, Any]:
        """Analyze student's complete profile"""
        # Extract all text from profile
        all_text = []
        
        # Add experience bullets
        for exp in profile.experiences:
            all_text.extend(exp.bullets)
            all_text.append(f"{exp.title} at {exp.organization}")
        
        # Add project descriptions
        for proj in profile.projects:
            all_text.extend(proj.bullets)
            all_text.append(proj.title)
        
        # Add skills
        all_text.extend(profile.skills.keys())
        
        # Extract keywords from student's content
        full_text = ' '.join(all_text).lower()
        student_keywords = self.keyword_extractor.extract_keywords(full_text)
        
        # Create bullet bank with embeddings
        bullet_bank = []
        for exp in profile.experiences:
            for bullet in exp.bullets:
                bullet_bank.append({
                    'text': bullet,
                    'source': f"{exp.title} at {exp.organization}",
                    'type': 'experience',
                    'embedding': self.embedding_model.encode(bullet)
                })
        
        for proj in profile.projects:
            for bullet in proj.bullets:
                bullet_bank.append({
                    'text': bullet,
                    'source': proj.title,
                    'type': 'project',
                    'embedding': self.embedding_model.encode(bullet)
                })
        
        profile.all_bullets = bullet_bank
        
        return {
            'total_experiences': len(profile.experiences),
            'total_projects': len(profile.projects),
            'total_skills': len(profile.skills),
            'keywords': student_keywords,
            'bullet_count': len(bullet_bank)
        }
    
    def calculate_match_score(self, profile: StudentProfile, job: JobPosting) -> float:
        """Calculate how well profile matches job"""
        score = 0.0
        max_score = 100.0
        
        # Check required skills (40 points)
        student_skills = set(skill.lower() for skill in profile.skills.keys())
        required_skills = set(skill.lower() for skill in job.skills_required)
        
        if required_skills:
            skill_match = len(student_skills & required_skills) / len(required_skills)
            score += skill_match * 40
        
        # Check experience years (20 points)
        if job.experience_years:
            # Calculate approximate student experience
            student_years = len(profile.experiences) * 0.5  # Rough estimate
            if student_years >= job.experience_years:
                score += 20
            else:
                score += (student_years / job.experience_years) * 20
        else:
            score += 20  # Full points if no requirement
        
        # Keyword matching (30 points)
        student_text = ' '.join([b['text'] for b in profile.all_bullets])
        keyword_matches = sum(1 for keyword in job.keywords[:10] if keyword in student_text.lower())
        score += (keyword_matches / 10) * 30
        
        # Bonus for nice-to-have skills (10 points)
        nice_skills = set(skill.lower() for skill in job.nice_to_have)
        if nice_skills:
            nice_match = len(student_skills & nice_skills) / len(nice_skills)
            score += nice_match * 10
        
        return min(score, 100.0)
    
    def select_best_bullets(self, profile: StudentProfile, job: JobPosting, max_bullets: int = 12) -> List[Dict[str, Any]]:
        """Select most relevant bullets for the job"""
        if not profile.all_bullets:
            return []
        
        # Create job embedding
        job_text = f"{job.title} {job.description} {' '.join(job.requirements)}"
        job_embedding = self.embedding_model.encode(job_text)
        
        # Score each bullet
        scored_bullets = []
        for bullet in profile.all_bullets:
            # Semantic similarity
            similarity = np.dot(bullet['embedding'], job_embedding) / (
                np.linalg.norm(bullet['embedding']) * np.linalg.norm(job_embedding)
            )
            
            # Keyword bonus
            keyword_bonus = sum(0.1 for keyword in job.keywords[:10] 
                              if keyword in bullet['text'].lower())
            
            # Action verb bonus
            has_action = any(bullet['text'].lower().startswith(verb) 
                           for verb in self.keyword_extractor.action_verbs)
            action_bonus = 0.1 if has_action else 0
            
            total_score = similarity + keyword_bonus + action_bonus
            
            scored_bullets.append({
                **bullet,
                'score': total_score,
                'similarity': similarity
            })
        
        # Sort and select top bullets
        scored_bullets.sort(key=lambda x: x['score'], reverse=True)
        
        # Ensure diversity - don't take all from same source
        selected = []
        source_count = {}
        
        for bullet in scored_bullets:
            source = bullet['source']
            if source_count.get(source, 0) < 3:  # Max 3 bullets per source
                selected.append(bullet)
                source_count[source] = source_count.get(source, 0) + 1
                
                if len(selected) >= max_bullets:
                    break
        
        return selected

# ============= Resume Tailor =============

class ResumeTailor:
    """Main system to tailor resumes for specific jobs"""
    
    def __init__(self):
        self.keyword_extractor = KeywordExtractor()
        self.analyzer = ResumeAnalyzer()
        
    def tailor_resume(self, profile: StudentProfile, job_posting: str, 
                      job_title: str, company: str) -> TailoredResume:
        """Create tailored resume for specific job"""
        
        # Parse job posting
        job = self.keyword_extractor.parse_job_posting(job_posting, job_title, company)
        
        # Analyze student profile
        self.analyzer.analyze_student_profile(profile)
        
        # Calculate match score
        match_score = self.analyzer.calculate_match_score(profile, job)
        
        # Select best bullets
        selected_bullets_data = self.analyzer.select_best_bullets(profile, job)
        selected_bullets = [b['text'] for b in selected_bullets_data]
        
        # Select most relevant experiences (max 3)
        scored_experiences = []
        for exp in profile.experiences:
            exp_text = f"{exp.title} {' '.join(exp.bullets)}"
            exp_keywords = set(exp_text.lower().split())
            job_keywords = set(job.keywords[:20])
            overlap = len(exp_keywords & job_keywords)
            scored_experiences.append((exp, overlap))
        
        scored_experiences.sort(key=lambda x: x[1], reverse=True)
        selected_experiences = [exp for exp, _ in scored_experiences[:3]]
        
        # Select most relevant projects (max 2)
        scored_projects = []
        for proj in profile.projects:
            proj_text = f"{proj.title} {' '.join(proj.bullets)}"
            proj_keywords = set(proj_text.lower().split())
            overlap = len(proj_keywords & job_keywords)
            scored_projects.append((proj, overlap))
        
        scored_projects.sort(key=lambda x: x[1], reverse=True)
        selected_projects = [proj for proj, _ in scored_projects[:2]]
        
        # Identify skills to highlight
        highlighted_skills = []
        for skill in profile.skills.keys():
            if skill.lower() in [s.lower() for s in job.skills_required]:
                highlighted_skills.append(skill)
        
        # Missing skills
        student_skills = set(skill.lower() for skill in profile.skills.keys())
        required_skills = set(skill.lower() for skill in job.skills_required)
        missing_skills = list(required_skills - student_skills)
        
        # Keywords to add
        current_keywords = set(' '.join(selected_bullets).lower().split())
        important_job_keywords = set(job.keywords[:15])
        keywords_to_add = list(important_job_keywords - current_keywords)[:10]
        
        # Generate improvement suggestions
        suggestions = []
        
        if missing_skills:
            suggestions.append(f"Consider learning: {', '.join(missing_skills[:3])}")
        
        if match_score < 70:
            suggestions.append("Add more relevant keywords from the job description")
        
        if len(selected_bullets) < 8:
            suggestions.append("Add more quantifiable achievements to your experiences")
        
        # Check for action verbs
        bullets_with_action = sum(1 for b in selected_bullets 
                                if any(b.lower().startswith(v) for v in self.keyword_extractor.action_verbs))
        if bullets_with_action < len(selected_bullets) * 0.7:
            suggestions.append("Start more bullets with strong action verbs")
        
        # Calculate ATS score
        ats_score = self._calculate_ats_score(selected_bullets, job)
        
        return TailoredResume(
            job_title=job_title,
            company=company,
            match_score=match_score,
            selected_experiences=selected_experiences,
            selected_projects=selected_projects,
            selected_bullets=selected_bullets,
            highlighted_skills=highlighted_skills,
            keywords_to_add=keywords_to_add,
            missing_skills=missing_skills,
            improvement_suggestions=suggestions,
            ats_score=ats_score
        )
    
    def _calculate_ats_score(self, bullets: List[str], job: JobPosting) -> float:
        """Calculate ATS compatibility score"""
        score = 0.0
        
        # Check for keywords (40%)
        all_text = ' '.join(bullets).lower()
        keyword_matches = sum(1 for keyword in job.keywords[:20] if keyword in all_text)
        score += (keyword_matches / 20) * 40
        
        # Check for skills (30%)
        skill_matches = sum(1 for skill in job.skills_required if skill.lower() in all_text)
        if job.skills_required:
            score += (skill_matches / len(job.skills_required)) * 30
        else:
            score += 30
        
        # Check formatting (30%)
        # Simple format checks
        format_score = 30
        for bullet in bullets:
            # Penalize special characters that ATS might not parse
            if any(char in bullet for char in ['→', '●', '◆', '★']):
                format_score -= 0.5
            # Penalize overly long bullets
            if len(bullet) > 150:
                format_score -= 0.3
        
        score += max(format_score, 0)
        
        return min(score, 100.0)
    
    def generate_resume_text(self, profile: StudentProfile, tailored: TailoredResume) -> str:
        """Generate formatted resume text"""
        resume = []
        
        # Header
        resume.append(f"{profile.name}")
        resume.append(f"{profile.email} | {profile.phone} | LinkedIn: {profile.linkedin}")
        if profile.github:
            resume.append(f"GitHub: {profile.github}")
        resume.append("\n")
        
        # Education
        resume.append("EDUCATION")
        resume.append("-" * 50)
        for edu in profile.education:
            resume.append(f"{edu.degree} in {edu.major}")
            resume.append(f"{edu.school}, Expected: {edu.graduation_date}")
            if edu.gpa and edu.gpa >= 3.5:
                resume.append(f"GPA: {edu.gpa}/4.0")
            if edu.coursework:
                resume.append(f"Relevant Coursework: {', '.join(edu.coursework[:4])}")
        resume.append("\n")
        
        # Skills (highlighted ones first)
        resume.append("TECHNICAL SKILLS")
        resume.append("-" * 50)
        
        # Organize skills by category
        skill_categories = {
            'Languages': [],
            'Frameworks': [],
            'Tools': [],
            'Other': []
        }
        
        for skill in tailored.highlighted_skills:
            # Simple categorization
            if skill.lower() in ['python', 'java', 'javascript', 'c++', 'c#', 'ruby', 'go']:
                skill_categories['Languages'].append(skill)
            elif skill.lower() in ['react', 'angular', 'django', 'flask', 'spring', 'node.js']:
                skill_categories['Frameworks'].append(skill)
            elif skill.lower() in ['git', 'docker', 'kubernetes', 'aws', 'jenkins']:
                skill_categories['Tools'].append(skill)
            else:
                skill_categories['Other'].append(skill)
        
        for category, skills in skill_categories.items():
            if skills:
                resume.append(f"{category}: {', '.join(skills)}")
        resume.append("\n")
        
        # Experience
        resume.append("EXPERIENCE")
        resume.append("-" * 50)
        
        # Map bullets to experiences
        for exp in tailored.selected_experiences:
            resume.append(f"{exp.title}")
            resume.append(f"{exp.organization} | {exp.location} | {exp.start_date} - {exp.end_date}")
            
            # Find bullets for this experience
            exp_bullets = [b for b in tailored.selected_bullets 
                          if any(b in orig_b for orig_b in exp.bullets)][:3]
            
            for bullet in exp_bullets:
                resume.append(f"• {bullet}")
            resume.append("")
        
        # Projects
        if tailored.selected_projects:
            resume.append("PROJECTS")
            resume.append("-" * 50)
            
            for proj in tailored.selected_projects:
                resume.append(f"{proj.title}")
                
                # Find bullets for this project
                proj_bullets = [b for b in tailored.selected_bullets 
                              if any(b in orig_b for orig_b in proj.bullets)][:2]
                
                for bullet in proj_bullets:
                    resume.append(f"• {bullet}")
                resume.append("")
        
        return "\n".join(resume)
    
    def generate_tips(self, tailored: TailoredResume) -> List[str]:
        """Generate specific tips for improving the resume"""
        tips = []
        
        if tailored.match_score < 60:
            tips.append("⚠️ Low match score. Consider gaining experience in the required areas.")
        elif tailored.match_score < 80:
            tips.append("📈 Good match! Add more relevant keywords to improve further.")
        else:
            tips.append("✨ Excellent match! Your profile aligns well with this position.")
        
        if tailored.missing_skills:
            tips.append(f"🎯 Key skills to add: {', '.join(tailored.missing_skills[:3])}")
        
        if tailored.keywords_to_add:
            tips.append(f"🔑 Include these keywords: {', '.join(tailored.keywords_to_add[:5])}")
        
        if tailored.ats_score < 70:
            tips.append("🤖 Improve ATS compatibility by using simpler formatting and more keywords")
        
        tips.append(f"📊 Your ATS Score: {tailored.ats_score:.0f}/100")
        tips.append(f"🎯 Job Match Score: {tailored.match_score:.0f}/100")
        
        return tips

# ============= Example Usage =============

def create_sample_profile() -> StudentProfile:
    """Create a sample student profile"""
    return StudentProfile(
        name="Alex Johnson",
        email="alex.johnson@university.edu",
        phone="(555) 123-4567",
        linkedin="linkedin.com/in/alexjohnson",
        github="github.com/alexj",
        
        education=[
            Education(
                degree="Bachelor of Science",
                major="Computer Science",
                school="State University",
                graduation_date="May 2024",
                gpa=3.7,
                coursework=["Data Structures", "Algorithms", "Web Development", "Machine Learning"]
            )
        ],
        
        experiences=[
            Experience(
                title="Software Engineering Intern",
                organization="Tech Corp",
                start_date="June 2023",
                end_date="August 2023",
                location="San Francisco, CA",
                bullets=[
                    "Developed RESTful APIs using Python and Flask, serving 10,000+ daily requests",
                    "Implemented automated testing suite, increasing code coverage from 45% to 80%",
                    "Collaborated with cross-functional team of 8 engineers on agile development",
                    "Optimized database queries, reducing response time by 35%"
                ]
            ),
            Experience(
                title="Web Developer",
                organization="University IT Department",
                start_date="September 2022",
                end_date="May 2023",
                location="Campus",
                bullets=[
                    "Built responsive web applications using React and Node.js",
                    "Maintained university portal serving 5,000+ students",
                    "Resolved 50+ bug tickets and feature requests",
                    "Trained 3 new student developers on codebase"
                ]
            )
        ],
        
        projects=[
            Experience(
                title="AI Study Buddy - Machine Learning Project",
                organization="Personal Project",
                start_date="January 2023",
                end_date="March 2023",
                location="",
                bullets=[
                    "Created ML model to predict study time needed for courses using Python and scikit-learn",
                    "Achieved 85% accuracy in time predictions using Random Forest algorithm",
                    "Built web interface with React for 100+ student users",
                    "Deployed on AWS using Docker containers"
                ]
            ),
            Experience(
                title="Campus Marketplace App",
                organization="Hackathon Project",
                start_date="November 2022",
                end_date="November 2022",
                location="",
                bullets=[
                    "Developed full-stack marketplace app in 48 hours using MERN stack",
                    "Implemented secure payment processing with Stripe API",
                    "Won 2nd place out of 30 teams"
                ]
            )
        ],
        
        skills={
            "Python": SkillLevel.ADVANCED,
            "JavaScript": SkillLevel.ADVANCED,
            "React": SkillLevel.INTERMEDIATE,
            "Node.js": SkillLevel.INTERMEDIATE,
            "SQL": SkillLevel.INTERMEDIATE,
            "Git": SkillLevel.ADVANCED,
            "AWS": SkillLevel.BEGINNER,
            "Docker": SkillLevel.BEGINNER,
            "Java": SkillLevel.INTERMEDIATE,
            "Machine Learning": SkillLevel.BEGINNER
        }
    )

def demo_resume_tailoring():
    """Demo the resume tailoring system"""
    print("\n" + "="*70)
    print("🎯 Smart Resume Tailoring System")
    print("="*70)
    
    # Create sample profile
    profile = create_sample_profile()
    print(f"\n📋 Student Profile: {profile.name}")
    print(f"   Education: {profile.education[0].major} at {profile.education[0].school}")
    print(f"   Experience: {len(profile.experiences)} positions")
    print(f"   Projects: {len(profile.projects)} projects")
    print(f"   Skills: {len(profile.skills)} technical skills")
    
    # Sample job posting
    job_posting = """
    Software Engineer - New Grad
    TechStart Inc. | San Francisco, CA
    
    We're looking for talented new graduates to join our engineering team!
    
    Requirements:
    • Bachelor's degree in Computer Science or related field
    • Strong programming skills in Python, Java, or JavaScript
    • Experience with web development (React, Node.js preferred)
    • Understanding of data structures and algorithms
    • Experience with version control (Git)
    • Strong problem-solving and communication skills
    
    Nice to have:
    • Experience with cloud platforms (AWS, GCP, Azure)
    • Knowledge of containerization (Docker, Kubernetes)
    • Machine learning experience
    • Open source contributions
    • Internship experience at tech companies
    
    What you'll do:
    • Build scalable web applications using modern frameworks
    • Collaborate with product and design teams
    • Write clean, maintainable code with proper testing
    • Participate in code reviews and technical discussions
    • Deploy and monitor applications in cloud environments
    
    We offer competitive salary, equity, and great benefits!
    """
    
    # Tailor resume
    print("\n" + "-"*50)
    print("📄 Job Posting: Software Engineer at TechStart Inc.")
    print("-"*50)
    
    tailor = ResumeTailor()
    tailored = tailor.tailor_resume(
        profile, 
        job_posting,
        "Software Engineer - New Grad",
        "TechStart Inc."
    )
    
    # Show results
    print(f"\n📊 ANALYSIS RESULTS")
    print(f"   Match Score: {tailored.match_score:.1f}%")
    print(f"   ATS Score: {tailored.ats_score:.1f}%")
    
    print(f"\n✅ Matching Skills: {', '.join(tailored.highlighted_skills[:5])}")
    print(f"❌ Missing Skills: {', '.join(tailored.missing_skills[:3])}")
    print(f"🔑 Keywords to Add: {', '.join(tailored.keywords_to_add[:5])}")
    
    print(f"\n📝 SELECTED CONTENT")
    print(f"   Experiences: {len(tailored.selected_experiences)} selected")
    for exp in tailored.selected_experiences:
        print(f"   • {exp.title} at {exp.organization}")
    
    print(f"\n   Projects: {len(tailored.selected_projects)} selected")
    for proj in tailored.selected_projects:
        print(f"   • {proj.title}")
    
    print(f"\n💡 IMPROVEMENT SUGGESTIONS")
    for i, suggestion in enumerate(tailored.improvement_suggestions, 1):
        print(f"   {i}. {suggestion}")
    
    # Generate tips
    tips = tailor.generate_tips(tailored)
    print(f"\n🎯 OPTIMIZATION TIPS")
    for tip in tips:
        print(f"   {tip}")
    
    # Generate resume text
    print(f"\n" + "="*70)
    print("📄 TAILORED RESUME")
    print("="*70)
    resume_text = tailor.generate_resume_text(profile, tailored)
    print(resume_text[:1500] + "...")  # Show first part
    
    print(f"\n" + "="*70)
    print("✅ Resume successfully tailored for Software Engineer at TechStart Inc.!")
    print("="*70)

if __name__ == "__main__":
    demo_resume_tailoring()
