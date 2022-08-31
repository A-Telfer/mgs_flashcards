from crypt import methods
import datetime
import random
from google.cloud import datastore

from flask import Flask, render_template, redirect, request

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
datastore_client = datastore.Client()

query = datastore_client.query(kind="Question")
questions = [q.id for q in list(query.fetch())]

def get_random_question(excluding=[]):
    question_with_excluded = list(set(questions) - set(excluding))
    
    if len(question_with_excluded) == 0: 
        return None
    
    question_index = random.randint(0, len(question_with_excluded)-1)
    return get_question(question_with_excluded[question_index])

def create_session():
    session_key = datastore_client.key("Session")
    session = datastore.Entity(key=session_key)
    session['questions'] = []
    datastore_client.put(session)
    return session

def get_session(id):
    key = datastore_client.key("Session", int(id))
    return datastore_client.get(key=key)

def get_question(id):
    key = datastore_client.key("Question", int(id))
    return datastore_client.get(key=key)

def get_session_answer(session, question_id):
    for q in session['questions']:
        if q["id"] == question_id:
            return q
        
    
@app.route('/sessions/<session_id>', methods=["GET"])
def show_all_questions(session_id):
    session_id = int(session_id)
    session = get_session(session_id)
    
    questions = []
    for answered in session['questions']:
        questions.append(dict(answered=answered, correct=get_question(answered["id"])))
    
    messages = []
    next=""
    return render_template(
        'answer.html', 
        questions=questions,
        next=next,
        messages=messages,
        session=session_id
    )
    
@app.route('/sessions/<session_id>/questions/<question_id>', methods=["POST", "GET"])
def question(session_id, question_id):
    question_id = int(question_id)
    session_id = int(session_id)
    
    session = get_session(session_id)
    question = get_question(question_id)
    session_question_ids = [q['id'] for q in session['questions']]
        
    if request.method == 'POST':
        # update session
        update = True
        messages = []
        if question_id in session_question_ids:
            messages.append(dict(
                text="Error: Could not update. Question has already been answered for this session.",
                color="red",
                icon="bi bi-exclamation-circle"
            ))
            update = False
        
        if update:
            session['questions'].append(
                dict(id=question.id, **{k: int(v) for k, v in request.form.items()})
            )
            datastore_client.put(session)
        
        answer = get_session_answer(session, question_id)
        next = get_random_question(session_question_ids)
        if next is not None:
            next = f"/sessions/{session.id}/questions/{next.id}"
            
        questions = [dict(correct=question, answered=answer)]
        return render_template(
            'answer.html', 
            questions=questions,
            next=next,
            messages = messages,
            session=session_id
        )
    
    elif request.method == 'GET':
        if question_id in session_question_ids:
            answer = get_session_answer(session, question_id)
            next = get_random_question(session_question_ids)
            if next is not None:
                next = f"/sessions/{session.id}/questions/{next.id}"
                
            return render_template(
                'answer.html', 
                question=question,
                answer=answer,
                next=next,
                session=session_id
            )
            
        return render_template(
            'question.html', 
            question=question,
            session=session_id
        )
    
@app.route('/')
def root():
    session = create_session()
    question = get_random_question()
    return redirect(f"/sessions/{session.id}/questions/{question.id}", code=302)

    
    
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)