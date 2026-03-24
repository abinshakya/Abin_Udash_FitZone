from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import json
from groq import Groq

def ai_chat(request):
    # Initialize chat history in session if it doesn't exist
    if 'chat_history' not in request.session:
        request.session['chat_history'] = [
            {'role': 'ai', 'content': "Hello! I'm your AI fitness assistant. How can I help you reach your goals today?"}
        ]

    return render(request, 'ai_chat.html', {
        'chat_history': request.session['chat_history']
    })

@csrf_exempt
def get_ai_response(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').strip()
            
            if not user_message:
                return JsonResponse({'error': 'No message provided'}, status=400)

            # Get history from session
            if 'chat_history' not in request.session:
                request.session['chat_history'] = [
                    {'role': 'ai', 'content': "Hello! I'm your AI fitness assistant. How can I help you reach your goals today?"}
                ]
            
            history = request.session['chat_history']
            history.append({'role': 'user', 'content': user_message})
            
            client = Groq(api_key=settings.GROQ_API_KEY)
            
            # Format messages for Groq including history
            messages = [{"role": "system", "content": "You are a helpful and professional AI fitness trainer for FitZone. Provide workout advice, nutrition tips, and motivation. IMPORTANT: Always format your response using Markdown (e.g., use **bold** for headings, bullet points for lists, and clear spacing between sections) so it is easy to read."}]
            for msg in history:
                role = "assistant" if msg['role'] == 'ai' else "user"
                messages.append({"role": role, "content": msg['content']})

            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
            )
            
            ai_response = completion.choices[0].message.content
            history.append({'role': 'ai', 'content': ai_response})
            
            # Save history back to session
            request.session['chat_history'] = history
            request.session.modified = True
            
            return JsonResponse({'response': ai_response})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request'}, status=400)
