from llmproxy import text_upload, pdf_upload

def upload_faq_text(user_id):
    try: 
        response = text_upload(
            text = """
# 20 Frequently Asked Questions for CS Graduate Advisors
# This is "faq.txt"

## 1. What are the core competency requirements for CS graduate students?
**Answer:** CS graduate students must complete at least one class in each of these four areas:
- Computer Architecture and Assembly Language (CA&AL)
- Programming Languages (PL)
- Data Structures and Analysis of Algorithms (DS&AA)
- Theory of Computation (ToC)
You must earn at least a B- in a course to satisfy a competency requirement. The handbook lists specific courses that fulfill each area.

**Reference:** CS Graduate Student Handbook Supplement, "Core Competencies" section, page 1-2

## 2. How many courses do I need to complete for my MS in Computer Science?
**Answer:** You need to complete 10 total courses (each of 3 SHUs or more). These can be a combination of standard courses (8-10) and research courses (0-2). All MS students must complete the core competency requirements by the end of their program.

**Reference:** CS Graduate Student Handbook Supplement, "M.S. in Computer Science" section, page 1-2

## 3. What's the difference between CS 293 (MS Project) and CS 295/296 (MS Thesis)?
**Answer:** CS 293 (MS Project) is a one-semester commitment (3 SHUs) involving research with a faculty advisor, while the MS thesis (CS 295 and CS 296) is a two-semester commitment requiring a committee, formal defense, and thesis document. The thesis requires finding a faculty member willing to supervise your work and approval from the CS Graduate committee.

**Reference:** CS Graduate Student Handbook Supplement, "M.S. Project" and "M.S. Thesis" sections, page 4

## 4. When should I take the PhD qualifying exam?
**Answer:** For PhD students without an MS: Take it during your third or fourth semester after satisfying core competencies. You must pass it by the end of your fifth semester.
For PhD students with an MS: Take it by the end of your second semester after satisfying core competencies. You must pass it by the end of your third semester.

**Reference:** CS Graduate Student Handbook Supplement, "Qualifying Exam" section, page 6-7

## 5. How do I apply for the Co-op Program?
**Answer:** To apply for the Co-op Program, you must:
1. Attend a required Graduate Co-op Information Session (typically held at the end of the semester)
2. Complete the Graduate Co-op Program Application by the deadline
3. Be in good academic standing with no extensions of time or reduced course loads
4. Have completed at least 18 credits toward your degree
5. Complete the required career development sessions

**Reference:** SOE Graduate Handbook, "Co-op Application Process" section, page 42-43

## 6. What are the requirements to maintain good academic standing?
**Answer:** To remain in good academic standing, a student may have only:
- One grade lower than B-, or
- One Unsatisfactory (U), or
- One Incomplete (I) that remains incomplete for more than one semester, or Permanent Incomplete (PI)
Credit is only awarded for courses with a grade of B- or better or Satisfactory (S).

**Reference:** CS Graduate Student Handbook Supplement, "Academic Standing", page 8; SOE Graduate Handbook, page 8-9

## 7. How many research courses can I take as part of my MS degree?
**Answer:** MS students can take up to 2 research courses (out of 10 total courses). These can include CS 191, CS 293 (MS Project), or CS 295/296 (MS Thesis). The handbook recommends that MS students interested in completing a thesis bias their course selection toward research courses.

**Reference:** CS Graduate Student Handbook Supplement, "M.S. in Computer Science" section, page 1

## 8. What happens if I receive a grade lower than B- in a course?
**Answer:** If you receive a grade lower than B-, you may retake the course only once to achieve credit. You should discuss options with your department. The original grade remains on your record, and you'll still only be allowed one grade lower than B- to maintain good academic standing.

**Reference:** SOE Graduate Handbook, "Academic Standing" section, point 2, page 8

## 9. What is the timeline for completing a PhD in Computer Science?
**Answer:** Full-time PhD candidates should aim to graduate within 5 years of matriculation. Extensions to a maximum of seven calendar years may be requested for extenuating circumstances. The program involves coursework, qualifying exam, prospectus, committee formation, and dissertation defense.

**Reference:** SOE Graduate Handbook, "Time Limitations for Completing Degrees" section, page 11

## 10. Can I transfer credits from courses I took at another university?
**Answer:** Yes, up to two courses may be transferred if they:
- Carry a grade of B- or better (no pass/fail courses)
- Have not been counted toward another degree
- Were earned in graduate-level courses at an accredited institution
- Were taken within the past five years
Departments may impose additional criteria.

**Reference:** SOE Graduate Handbook, "Transfer of Credit" section, page 18

## 11. What is the process for forming a thesis committee for my MS thesis?
**Answer:** For an MS thesis, you and your advisor will jointly select a thesis committee, subject to approval by the CS Graduate Committee. The committee must include at least three faculty members, including one member from outside the department. You'll defend your research via a 45-minute public presentation.

**Reference:** CS Graduate Student Handbook Supplement, "M.S. Thesis" section, page 4

## 12. What is CS 191, and can it count toward my degree requirements?
**Answer:** CS 191 is a vehicle for doing research with similar requirements to the MS project. It can be taken at most once and counted as one of your research courses toward your degree requirements.

**Reference:** CS Graduate Student Handbook Supplement, "CS 191" section, page 4

## 13. What are the residency requirements for graduate programs?
**Answer:** For MS programs in Computer Science, you must be in residence (enrolled as Tufts SOE graduate students) for a minimum of 60% of your required graduate program credits, exclusive of graduate seminars. For doctoral programs, the residency requirement is two semesters, excluding summer.

**Reference:** SOE Graduate Handbook, "Residency Requirements" section, page 10

## 14. How do I submit a prospectus for my PhD?
**Answer:** You must submit a prospectus to the CS graduate committee six months after your qualifying exam. The prospectus should be 2-3 pages long describing your intended research direction, including a title, related work, and identifying your advisor and two additional committee members from the CS department. It must be signed by your advisor.

**Reference:** CS Graduate Student Handbook Supplement, "Prospectus" section, page 7 and Appendix B, page 19

## 15. How long do I have to complete my MS degree?
**Answer:** Master's degree candidates must complete all requirements in two years (four semesters, not including summers) after matriculation. A fifth semester is only allowed for a life event, with approval from the graduate dean. Part-time MS candidates must complete all requirements within five calendar years.

**Reference:** SOE Graduate Handbook, "Time Limitations for Completing Degrees" section, page 11

## 16. What is the dissertation committee composition for PhD students?
**Answer:** The doctoral committee consists of a minimum of five members:
- CS Faculty Advisor (with or without tenure)
- CS Faculty Member (with tenure)
- CS Faculty Member (with or without tenure)
- Tufts Faculty Member Outside of CS
- Member Outside of Tufts (doctoral-level researcher from university or industry)

**Reference:** CS Graduate Student Handbook Supplement, "Dissertation Committee" section, page 7-8

## 17. Is there a TA requirement for PhD students?
**Answer:** Yes, PhD students must TA at least one course during their time as a student at Tufts.

**Reference:** CS Graduate Student Handbook Supplement, "Teaching Assistantship" section, page 6

## 18. Can I take courses from other departments to fulfill my degree requirements?
**Answer:** Yes, but students focusing on an interdisciplinary area who want to take fewer than six CS courses require prior planning and approval. You should prepare a document explaining your plan, reasoning, and how you'll satisfy depth and breadth requirements, then have it approved by your advisor and submitted to the CS main office.

**Reference:** CS Graduate Student Handbook Supplement, Appendix F, page 21

## 19. What is the process for applying for graduation?
**Answer:** You need to apply for graduation in SIS and submit the online Graduate Degree Sheet. For certificates, you must submit the online Recommendation for Award of Certificate form. All requirements must be completed by the deadlines listed on the registrar's website.

**Reference:** SOE Graduate Handbook, "Procedure for Awarding of Certificates and Degrees" section, page 35

## 20. What happens during a dissertation defense?
**Answer:** A dissertation defense consists of two parts:
1. A formal public presentation of your research to the Tufts community and invited guests
2. A closed session with your committee members

You must distribute your dissertation to committee members in advance, and submit the final approved document to ProQuest after making any committee-recommended revisions. The defense should be scheduled several weeks before the thesis/dissertation submission deadline.

**Reference:** SOE Graduate Handbook, "Thesis/Dissertation Defense and Submission" section, page 36; CS Graduate Student Handbook Supplement, "Dissertation Defense" section, page 8
            """,
            session_id = 'cs-advising-faq-v2' + user_id,
            strategy = 'smart')
        
        print("✅ FAQ text loaded successfully")

    except Exception as e:
        print(f"❌ Error loading FAQ: {str(e)}")


def handbook_upload(user_id):
    try:
        all_references = ["cs_handbook.pdf", "filtered_grad_courses.pdf"]
        for reference in all_references:
            response = pdf_upload(
                path = f'resources/{reference}',
                session_id = 'cs-advising-handbooks-v5-' + user_id,
                strategy = 'smart'
            )
            print("✅ " + reference + " is successfully loaded")

    except Exception as e:
        print(f"❌ Error uploading handbooks: {str(e)}")

