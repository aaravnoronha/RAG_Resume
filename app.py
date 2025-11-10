"""
Resume Tailor Web Interface
Interactive web app for students to optimize their resumes
"""

import streamlit as st
import json
from datetime import datetime
from resume_tailor import (
    ResumeTailor, StudentProfile, Education, Experience,
    SkillLevel, create_sample_profile
)

# Page config
st.set_page_config(
    page_title="Resume Tailor for Students",
    page_icon="🎯",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .match-score {
        font-size: 48px;
        font-weight: bold;
        text-align: center;
    }
    .score-good { color: #00c853; }
    .score-medium { color: #ffab00; }
    .score-low { color: #d32f2f; }
    .tip-box {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .keyword-tag {
        background-color: #e3f2fd;
        color: #1976d2;
        padding: 5px 10px;
        border-radius: 15px;
        margin: 2px;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session():
    """Initialize session state"""
    if 'profile' not in st.session_state:
        st.session_state.profile = None
    if 'tailored_results' not in st.session_state:
        st.session_state.tailored_results = None
    if 'step' not in st.session_state:
        st.session_state.step = 1

def sidebar_profile_builder():
    """Build student profile in sidebar"""
    with st.sidebar:
        st.header("👤 Your Profile")
        
        # Use sample or build custom
        profile_option = st.radio(
            "Choose option:",
            ["Use Sample Profile", "Build Custom Profile"]
        )
        
        if profile_option == "Use Sample Profile":
            if st.button("Load Sample Profile"):
                st.session_state.profile = create_sample_profile()
                st.success("Sample profile loaded!")
        
        else:
            st.subheader("Basic Information")
            name = st.text_input("Full Name", "Alex Johnson")
            email = st.text_input("Email", "alex@university.edu")
            phone = st.text_input("Phone", "(555) 123-4567")
            linkedin = st.text_input("LinkedIn URL", "linkedin.com/in/alex")
            github = st.text_input("GitHub URL (optional)", "github.com/alex")
            
            st.subheader("Education")
            degree = st.selectbox("Degree", ["Bachelor of Science", "Bachelor of Arts", "Master of Science"])
            major = st.text_input("Major", "Computer Science")
            school = st.text_input("School", "State University")
            grad_date = st.text_input("Graduation Date", "May 2024")
            gpa = st.number_input("GPA (optional)", 0.0, 4.0, 3.7, 0.1)
            
            st.subheader("Skills")
            st.write("Add your technical skills:")
            
            skills = {}
            skill_input = st.text_input("Skill (press Enter to add)", key="skill_input")
            skill_level = st.selectbox("Level", ["Beginner", "Intermediate", "Advanced"])
            
            if st.button("Add Skill"):
                if skill_input:
                    skills[skill_input] = SkillLevel[skill_level.upper()]
                    st.success(f"Added {skill_input}")
            
            st.subheader("Experience")
            exp_title = st.text_input("Position Title", "Software Engineering Intern")
            exp_company = st.text_input("Company", "Tech Corp")
            exp_bullets = st.text_area(
                "Achievements (one per line)",
                "Developed REST APIs using Python and Flask\nIncreased code coverage from 45% to 80%"
            )
            
            if st.button("Create Profile"):
                profile = StudentProfile(
                    name=name,
                    email=email,
                    phone=phone,
                    linkedin=linkedin,
                    github=github,
                    education=[Education(
                        degree=degree,
                        major=major,
                        school=school,
                        graduation_date=grad_date,
                        gpa=gpa if gpa > 0 else None
                    )],
                    experiences=[Experience(
                        title=exp_title,
                        organization=exp_company,
                        start_date="June 2023",
                        end_date="August 2023",
                        location="San Francisco, CA",
                        bullets=exp_bullets.split('\n') if exp_bullets else []
                    )],
                    skills=skills if skills else {"Python": SkillLevel.INTERMEDIATE}
                )
                st.session_state.profile = profile
                st.success("Profile created successfully!")

def main_app():
    """Main application interface"""
    
    # Header
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🎯 Smart Resume Tailor")
        st.markdown("*Optimize your resume for any job posting using AI-powered keyword matching*")
    
    # Check if profile exists
    if not st.session_state.profile:
        st.warning("👈 Please create or load your profile in the sidebar first!")
        return
    
    # Profile summary
    with st.expander("📋 Your Profile Summary", expanded=False):
        profile = st.session_state.profile
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Experiences", len(profile.experiences))
        with col2:
            st.metric("Projects", len(profile.projects))
        with col3:
            st.metric("Skills", len(profile.skills))
    
    # Job posting input
    st.header("📄 Step 1: Paste Job Posting")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        job_title = st.text_input("Job Title", "Software Engineer - New Grad")
        company = st.text_input("Company Name", "TechStart Inc.")
        
        job_posting = st.text_area(
            "Paste the full job description here:",
            height=300,
            placeholder="""Paste the job posting here...
            
Include all requirements, responsibilities, and qualifications.
The more complete the posting, the better the optimization!"""
        )
    
    with col2:
        st.info("""
        **Tips for best results:**
        - Include the entire job posting
        - Keep formatting (bullet points, sections)
        - Include both required and preferred qualifications
        """)
    
    # Analyze button
    if st.button("🚀 Analyze & Tailor Resume", type="primary", use_container_width=True):
        if job_posting and len(job_posting) > 100:
            with st.spinner("Analyzing job posting and optimizing resume..."):
                # Perform tailoring
                tailor = ResumeTailor()
                tailored = tailor.tailor_resume(
                    st.session_state.profile,
                    job_posting,
                    job_title,
                    company
                )
                st.session_state.tailored_results = tailored
                st.session_state.step = 2
        else:
            st.error("Please paste a complete job posting (at least 100 characters)")
    
    # Show results
    if st.session_state.tailored_results and st.session_state.step == 2:
        st.header("📊 Step 2: Analysis Results")
        
        tailored = st.session_state.tailored_results
        
        # Match scores
        col1, col2, col3 = st.columns(3)
        
        with col1:
            score_class = "score-good" if tailored.match_score >= 80 else \
                         "score-medium" if tailored.match_score >= 60 else "score-low"
            st.markdown(f"""
                <div class="match-score {score_class}">
                    {tailored.match_score:.0f}%
                </div>
                <p style="text-align: center;">Job Match Score</p>
            """, unsafe_allow_html=True)
        
        with col2:
            ats_class = "score-good" if tailored.ats_score >= 80 else \
                       "score-medium" if tailored.ats_score >= 60 else "score-low"
            st.markdown(f"""
                <div class="match-score {ats_class}">
                    {tailored.ats_score:.0f}%
                </div>
                <p style="text-align: center;">ATS Compatibility</p>
            """, unsafe_allow_html=True)
        
        with col3:
            skill_match = len(tailored.highlighted_skills)
            total_required = len(tailored.highlighted_skills) + len(tailored.missing_skills)
            skill_percentage = (skill_match / total_required * 100) if total_required > 0 else 0
            
            skill_class = "score-good" if skill_percentage >= 80 else \
                         "score-medium" if skill_percentage >= 60 else "score-low"
            st.markdown(f"""
                <div class="match-score {skill_class}">
                    {skill_match}/{total_required}
                </div>
                <p style="text-align: center;">Skills Matched</p>
            """, unsafe_allow_html=True)
        
        # Skills analysis
        st.header("🎯 Skills Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("✅ Your Matching Skills")
            for skill in tailored.highlighted_skills[:10]:
                st.markdown(f'<span class="keyword-tag">{skill}</span>', unsafe_allow_html=True)
        
        with col2:
            st.subheader("🎓 Skills to Learn")
            for skill in tailored.missing_skills[:10]:
                st.markdown(f'<span class="keyword-tag" style="background-color: #ffebee; color: #c62828;">{skill}</span>', unsafe_allow_html=True)
        
        # Keywords to add
        st.header("🔑 Keywords to Include")
        st.write("Add these keywords naturally throughout your resume:")
        
        keywords_html = ""
        for keyword in tailored.keywords_to_add[:15]:
            keywords_html += f'<span class="keyword-tag">{keyword}</span> '
        st.markdown(keywords_html, unsafe_allow_html=True)
        
        # Selected content
        st.header("📝 Optimized Content Selection")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Selected Experiences")
            for exp in tailored.selected_experiences:
                st.write(f"✓ **{exp.title}** at {exp.organization}")
        
        with col2:
            st.subheader("Selected Projects")
            for proj in tailored.selected_projects:
                st.write(f"✓ **{proj.title}**")
        
        # Top bullets
        st.subheader("🎯 Your Best Bullet Points")
        st.write("These achievements best match the job requirements:")
        
        for i, bullet in enumerate(tailored.selected_bullets[:5], 1):
            st.write(f"{i}. {bullet}")
        
        # Improvement suggestions
        st.header("💡 Improvement Suggestions")
        
        for suggestion in tailored.improvement_suggestions:
            st.info(suggestion)
        
        # Tips
        tips = ResumeTailor().generate_tips(tailored)
        
        st.header("📌 Optimization Tips")
        
        tip_cols = st.columns(2)
        for i, tip in enumerate(tips):
            with tip_cols[i % 2]:
                st.write(tip)
        
        # Generate resume button
        st.header("📄 Step 3: Generate Tailored Resume")
        
        if st.button("Generate Resume Text", type="primary", use_container_width=True):
            resume_text = ResumeTailor().generate_resume_text(
                st.session_state.profile,
                tailored
            )
            
            st.text_area(
                "Your Tailored Resume (Copy and format in your preferred editor):",
                resume_text,
                height=600
            )
            
            # Download button
            st.download_button(
                label="📥 Download as Text File",
                data=resume_text,
                file_name=f"resume_{company.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain"
            )
        
        # New job button
        if st.button("📝 Tailor for Another Job"):
            st.session_state.tailored_results = None
            st.session_state.step = 1
            st.rerun()

def main():
    """Main application"""
    initialize_session()
    
    # Sidebar
    sidebar_profile_builder()
    
    # Main content
    main_app()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666;">
        <p>🎯 Smart Resume Tailor | Built to help students land their dream jobs</p>
        <p>Remember: This tool helps optimize your resume, but authentic experiences and skills matter most!</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
