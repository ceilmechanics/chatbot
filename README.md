# TODOs:

## Human-in-the-loop
* [x] Provide more instructions for the thread, when LLM is not confident with the answer. Make it clear what the right hand side windows are for.
* [ ] Email plugin
* [ ] Reducing advisor workload: Adding ✅ or ❌ buttons to approve or modify AI-drafted responses

## Usability
* [x] Loading bar
* [ ] Advisor Q&A portal
* [x] FAQ format, make sure the FAQ format stored in DB are well-markdown formatted.
   * [x] Single quote/double quote consistency
   * [x] Bullet points should be well-represented in markdown formats

## Prompt
* [x] Lastk
   * [x] How long lastk should exist? Every week?
* [ ] When user is repeatedly asking questions in the same topic, consider escalate to the human advisor
* [x] Included soe-grad-handbook.pdf for comprehensive answers
* [ ] Incorporate Web Search API (Google Search) to answer more questions
   * [ ] Professor info
   * [ ] Courses info
* [ ] Add reference links in attachment (similar to GPT-4o)
   * [x] Handbook link (encoded citation links using markdown in response)
   * [ ] Tufts website (professor info, courses info)
