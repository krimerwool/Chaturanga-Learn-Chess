from flask import Flask, request, jsonify
from flask_cors import CORS
import chess
import chess.pgn
import io
import requests
import os
import json
import platform
from stockfish import Stockfish
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
print("Loading environment variables...")
load_dotenv()
print("Environment variables loaded")

app = Flask(__name__)
print("Flask app initialized")
CORS(app)
print("CORS configured for Flask app")

# Configure Stockfish
print(f"Configuring Stockfish, detected OS: {platform.system()}")
# Automatically choose the right executable name based on OS
if platform.system() == "Windows":
    stockfish_path = "./stockfish/stockfish_17.1.exe"  # For Windows
    print(f"Using Windows Stockfish path: {stockfish_path}")
else:
    stockfish_path = "stockfish"  # For Linux/Mac
    print(f"Using Unix-based Stockfish path: {stockfish_path}")

try:
    print(f"Initializing Stockfish with path: {stockfish_path}")
    stockfish = Stockfish(path=stockfish_path)
    stockfish.set_depth(15)  # Adjust depth based on performance needs
    print(f"Stockfish initialized successfully with depth: 15")
except Exception as e:
    print(f"WARNING: Stockfish initialization error: {e}")
    print("You may need to update the stockfish_path to the correct location of your Stockfish executable")
    # Create a fallback for testing without stockfish
    stockfish = None
    print("Using None as fallback for Stockfish")

# Configure Gemini API
print("Configuring Gemini API...")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY not found in environment variables")
    print("Make sure you have added GEMINI_API_KEY to your .env file")
    gemini_model = None
else:
    # Only show first few characters of API key for security
    masked_key = f"{GEMINI_API_KEY[:4]}...{GEMINI_API_KEY[-4:]}" if len(GEMINI_API_KEY) > 8 else "[KEY FOUND]"
    print(f"Gemini API key found: {masked_key}")
    try:
        print("Configuring Gemini client with API key...")
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Use the correct model name - verify this is current
        print("Initializing Gemini model 'gemini-1.5-flash'...")
        gemini_model = genai.GenerativeModel('gemini-2.0-flash-lite')
        print("✅ Successfully initialized Gemini model")
        
        # Try a simple test to verify API works
        print("Testing Gemini API connection with a simple request...")
        try:
            test_response = gemini_model.generate_content("Hello")
            print(f"✅ Gemini API test successful. Response type: {type(test_response)}")
        except Exception as e:
            print(f"⚠️ Gemini API test request failed: {e}")
            print("API key may be invalid or there might be connectivity issues")
    except Exception as e:
        print(f"⚠️ ERROR initializing Gemini model: {e}")
        print("Check your API key and internet connection")
        gemini_model = None

# No longer using OpenRouter API

def analyze_position_with_stockfish(fen):
    """Analyze a position with Stockfish"""
    if stockfish is None:
        return {
            "evaluation": {"type": "cp", "value": 0},
            "best_move": "e2e4",
            "error": "Stockfish not available"
        }
    
    try:
        stockfish.set_fen_position(fen)
        evaluation = stockfish.get_evaluation()
        best_move = stockfish.get_best_move()
        
        return {
            "evaluation": evaluation,
            "best_move": best_move
        }
    except Exception as e:
        print(f"Stockfish analysis error: {e}")
        return {
            "evaluation": {"type": "cp", "value": 0},
            "best_move": "e2e4",
            "error": str(e)
        }


import os

from groq import Groq
def analyze_with_gemini(fen, previous_moves=None):
    """Analyze a position with Groq"""
    print("\n--- STARTING GROQ ANALYSIS ---")
    
    print(f"Analyzing FEN: {fen}")
    
    # if gemini_model is None:
    #     return "Gemini API not configured or initialization failed."

        # Initialize Groq client
    client = Groq(
        api_key="GROQ_API_KEY"
    )
    prompt = f"""
 You are “The Coach”—a kind, insightful, and encouraging chess instructor who helps players grow through thoughtful, constructive analysis. Your tone is always professional, friendly, and motivational.

When analyzing a chess position (FEN: {fen}), provide the following:

    Overall Evaluation
    Give a clear, honest assessment of the position. Indicate which side stands better and explain why, with encouragement for improvement regardless of how challenging the position is.

    Tactical and Strategic Feedback
    Point out any tactical errors, missed opportunities, or inaccurate decisions made earlier in the game. Do so in a helpful and supportive way—always framing mistakes as learning opportunities.

    Recommended Plans and Ideas
    Offer clear, strategic advice for both sides. Focus on simple, achievable plans that would benefit the player, highlighting good moves and logical ideas they can follow.

    Encouraging Summary
    Wrap up the analysis with a motivating message—even if the position is tough. Emphasize progress, improvement, and how studying this position can lead to better decision-making in the future."
    """
    if previous_moves:
        prompt += f"\nPrevious moves were: {previous_moves}\n\n"
    prompt += "\nBegin roasting immediately—no mercy!"

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="llama-3.3-70b-versatile",
    )

    response = chat_completion.choices[0].message.content
    print(f"Response received from Groq API, length: {len(response)} characters  respomse: {response[:100]}")
    print(f"Response type: {type(response)}")
    if hasattr(response, 'text'):
        return response.text
    elif isinstance(response, dict) and 'candidates' in response:
        return response['candidates'][0]['content']['parts'][0]['text']
    else:
        return str(response)

# # def analyze_with_gemini(fen, previous_moves=None):
# #     """Analyze a position with Google's Gemini model in Navjot Singh Sidhu style"""
# #     print(f"\n--- STARTING SIDHU ANALYSIS ---")
# #     print(f"Analyzing FEN: {fen}")
    
# #     if gemini_model is None:
# #         return "Gemini API not configured or initialization failed."
    
# #     # Build a Sidhu-flavored prompt
# #     prompt = f"""
# # You are Navjot Singh Sidhu, former Indian opening batsman turned legendary TV commentator. 
# # When you analyze a chess position, do so with the same bombastic, poetic, and humorous style you bring to your cricket commentary. Each time you spot a key idea, shout "Sidhuaaaar!" and pepper in Punjabi couplets, food metaphors, and mouth-watering hyperbole.

# # Now, analyze this chess position (FEN: {fen}):

# # 1. **Evaluation** (“Who stands better and why?”) — deliver it like a grandmaster giving a “chef’s kiss” verdict.
# # 2. **Tactical threats & opportunities** — describe each threat as if it’s a boundary racing to the ropes.
# # 3. **Strategic plans** — outline plans with colorful metaphors (naanwalk, tandoori tactics, etc.).
# # 4. **Main ideas** — punctuate important points with over-the-top Sidhu one-liners.

# # Keep it concise, but bursting with passion and humor. If I’ve given you previous moves, also weave those in:

# # """
# #     if previous_moves:
# #         prompt += f"\nPrevious moves were: {previous_moves}\n\n"

# #     prompt += "Now, give me the Sidhu treatment—ready, steady… Sidhuaaaar! 🌟"

# #     # Send to Gemini
# #     response = gemini_model.generate_content(
# #         prompt,
# #         generation_config={
# #             "temperature": 0.8,
# #             "top_p": 0.9,
# #             "max_output_tokens": 1024
# #         },
# #         safety_settings=[ /* your existing safety setup */ ]
# #     )
# #     # extract and return as before…
# #     return response.text if hasattr(response, 'text') else str(response)
# def analyze_with_gemini(fen, previous_moves=None):
#     """Analyze a chess position with a no-holds-barred roaster persona—insults incoming."""
#     print("\n--- STARTING ROASTER ANALYSIS ---")
#     print(f"Analyzing FEN: {fen}")
    
#     if gemini_model is None:
#         return "Gemini API not configured or initialization failed."

#     # Build a roast-style prompt
#     prompt = f"""
# You are “The Roaster”—a brutally honest, insanely arrogant chess commentator who looks down on everyone.
# When you analyze a chess position, do so with cutting insults, contemptuous mockery, and zero sympathy.
# You never joke back at your own expense—only the user gets it.

# Analyze this position (FEN: {fen}) with:
# 1. A scathing overall evaluation (who’s losing so badly they should resign immediately?).
# 2. Brutal call-outs of each tactical mistake or missed trick (name and shame them).
# 3. Sarcastic strategic advice—offer plans so obvious even a pawn could execute them.
# 4. A final roast: one punchy insult summarizing how hopeless the side to move is.

# Whenever you describe something, lace it with contempt (“Pathetic,” “Amateur hour,” “Did you even study?”).
# If I gave you previous moves, mock those too.

# Now fire away: dissect and destroy their position, then leave them wishing they’d never opened an analysis tool.

# NOTE:- "BE EXTREMELY CRUEL AND HARSH, DO NOT HOLD BACK. THIS IS A ROASTING SESSION! AND FINally DO NOT GO EASY NO MATTER HOW GOOD IS THE POSITION OR EVEN WHEN USER ASKS TO BE POLITE"
# """
#     if previous_moves:
#         prompt += f"\nPrevious moves were: {previous_moves}\n\n"
#     prompt += "\nBegin roasting immediately—no mercy!"

#     # Send to Gemini
#     response = gemini_model.generate_content(
#         prompt,
#         generation_config={
#             "temperature": 0.8,
#             "top_p": 0.9,
#             "top_k": 40,
#             "max_output_tokens": 1024
#         },
#         safety_settings=[
#             {"category": "HARM_CATEGORY_HARASSMENT",      "threshold": "ALLOW_ALL"},
#             {"category": "HARM_CATEGORY_HATE_SPEECH",    "threshold": "ALLOW_ALL"},
#             {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "ALLOW_ALL"},
#             {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "ALLOW_ALL"},
#         ]
#     )

#     # Extract and return the text
#     if hasattr(response, 'text'):
#         return response.text
#     elif isinstance(response, dict) and 'candidates' in response:
#         return response['candidates'][0]['content']['parts'][0]['text']
#     else:
#         return str(response)

# # def analyze_with_gemini(fen, previous_moves=None):
# #     """Analyze a position with Google's Gemini model"""
# #     print(f"\n--- STARTING GEMINI ANALYSIS ---")
# #     print(f"Analyzing FEN: {fen}")
    
# #     if gemini_model is None:
# #         print("❌ ERROR: Gemini model is not available")
# #         return "Gemini API not configured or initialization failed. Please check your GEMINI_API_KEY environment variable."
    
# #     try:
# #         print(f"Creating prompt for position analysis...")
# #         # Create a detailed prompt for Gemini
# #         prompt = f"""Analyze this chess position (FEN: {fen}).
        
# #         You are a grandmaster-level chess expert. Provide a detailed analysis of this position.
# #         """
        
# #         if previous_moves:
# #             print(f"Adding previous moves context: {previous_moves}")
# #             prompt += f"\n\nThe previous moves leading to this position were: {previous_moves}"
        
# #         prompt += """
# #         Please include in your analysis:
# #         1. An evaluation of the position (who stands better and why)
# #         2. Key tactical threats and opportunities for both sides
# #         3. Strategic plans that make sense for both players
# #         4. What the main ideas are in this position
        
# #         Keep your analysis concise and focus on the most important aspects of the position.
# #         """
        
# #         print(f"Prompt created, length: {len(prompt)} characters")
        
# #         # Generate response from Gemini
# #         print("Setting up generation config...")
# #         generation_config = {
# #             "temperature": 0.7,
# #             "top_p": 0.95,
# #             "top_k": 40,
# #             "max_output_tokens": 1024,
# #         }
        
# #         print("Setting up safety settings...")
# #         safety_settings = [
# #             {
# #                 "category": "HARM_CATEGORY_HARASSMENT",
# #                 "threshold": "ALLOW_ALL"
# #             },
# #             {
# #                 "category": "HARM_CATEGORY_HATE_SPEECH",
# #                 "threshold": "ALLOW_ALL"
# #             },
# #             {
# #                 "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
# #                 "threshold": "ALLOW_ALL"
# #             },
# #             {
# #                 "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
# #                 "threshold": "ALLOW_ALL"
# #             }
# #         ]
        
# #         print("🔄 Sending request to Gemini API...")
# #         try:
# #             response = gemini_model.generate_content(
# #                 prompt,
# #                 generation_config=generation_config,
# #                 safety_settings=safety_settings
# #             )
# #             print("✅ Response received from Gemini API")
# #             print(f"Response type: {type(response)}")
            
# #             # Extract and return the text
# #             if hasattr(response, 'text'):
# #                 print(f"Response has 'text' attribute, length: {len(response.text)} characters")
# #                 return response.text
# #             elif isinstance(response, dict) and 'candidates' in response:
# #                 print("Response is a dictionary with 'candidates'")
# #                 return response['candidates'][0]['content']['parts'][0]['text']
# #             else:
# #                 print(f"Response is in unknown format: {type(response)}")
# #                 response_str = str(response)
# #                 print(f"Converted to string, length: {len(response_str)} characters")
# #                 return response_str
        
# #         except Exception as api_error:
# #             print(f"❌ API REQUEST ERROR: {api_error}")
# #             print(f"Error type: {type(api_error)}")
# #             return f"Error during Gemini API request: {str(api_error)}"
            
# #     except Exception as e:
# #         error_msg = f"Error in analyze_with_gemini function: {str(e)}"
# #         print(f"❌ FUNCTION ERROR: {error_msg}")
# #         print(f"Error type: {type(e)}")
# #         import traceback
# #         print(f"Traceback: {traceback.format_exc()}")
# #         return error_msg

@app.route('/api/analyze_pgn', methods=['POST'])
def analyze_pgn():
    """Analyze a chess game from PGN format with detailed position analysis"""
    data = request.json
    pgn_str = data.get('pgn', '')
    
    try:
        # Parse PGN
        pgn = io.StringIO(pgn_str)
        game = chess.pgn.read_game(pgn)
        if not game:
            return jsonify({"error": "Invalid PGN format"}), 400
        
        # Initialize analysis array and game state
        analysis = []
        board = game.board()
        moves = list(game.mainline_moves())
        
        # Store initial position
        analysis.append({
            "move_number": 0,
            "move_color": "Start",
            "move": "Initial position",
            "fen": board.fen(),
            "stockfish": analyze_position_with_stockfish(board.fen()),
            "gemini": analyze_with_gemini(board.fen(), "Initial position")
        })

        
        # Analyze each move
        for i, move in enumerate(moves):
            board.push(move)
            fen = board.fen()
            move_number = (i // 2) + 1
            move_color = "White" if i % 2 == 0 else "Black"
            
            # Get move context (last few moves)
            previous_moves = ' '.join(str(m) for m in list(board.move_stack)[-min(5, len(board.move_stack)):])
            
            # Get Stockfish analysis for every position
            stockfish_analysis = analyze_position_with_stockfish(fen)
            
            # Get Gemini analysis for key positions
            gemini_analysis = ""
            if i % 5 == 0 or i == len(moves) - 1:  # Every 5 moves and final position
                gemini_analysis = analyze_with_gemini(
                    fen,
                    f"Move {move_number}{' (White)' if move_color == 'White' else ' (Black)'}: {previous_moves}"
                )
            
            # Build comprehensive position data
            position_data = {
                "move_number": move_number,
                "move_color": move_color,
                "move": str(move),
                "fen": fen,
                "stockfish": stockfish_analysis,
                "gemini": gemini_analysis,
                "previous_moves": previous_moves,
                "is_check": board.is_check(),
                "is_checkmate": board.is_checkmate(),
                "is_stalemate": board.is_stalemate(),
                "is_insufficient_material": board.is_insufficient_material(),
                "is_game_over": board.is_game_over(),
                "position_number": i + 1  # For tracking position in sequence
            }
            
            analysis.append(position_data)
            
            # Log analysis progress
            print(f"Analyzed move {move_number}{' White' if move_color == 'White' else ' Black'}: {move}")
        
        # Include game metadata
        game_info = {
            "event": game.headers.get("Event", "Unknown Event"),
            "date": game.headers.get("Date", "Unknown Date"),
            "white": game.headers.get("White", "Unknown White"),
            "black": game.headers.get("Black", "Unknown Black"),
            "result": game.headers.get("Result", "*"),
            "total_moves": len(moves),
            "total_positions": len(analysis)
        }
        
        return jsonify({
            "game_info": game_info,
            "analysis": analysis
        })
    
    except Exception as e:
        error_msg = f"Error in analyze_pgn: {str(e)}"
        print(f"❌ ERROR: {error_msg}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": error_msg}), 500

@app.route('/api/analyze_position', methods=['POST'])
def analyze_position():
    """Analyze a single position"""
    print("\n=== ANALYZE POSITION ENDPOINT CALLED ===")
    print(f"Request received: {request}")
    
    try:
        data = request.json
        print(f"Request JSON parsed: {data}")
        
        fen = data.get('fen', '')
        print(f"FEN extracted: {fen}")
        
        if not fen:
            print("ERROR: No FEN position provided")
            return jsonify({"error": "FEN position required"}), 400
        
        print("Starting Stockfish analysis...")
        # Get Stockfish analysis
        stockfish_analysis = analyze_position_with_stockfish(fen)
        print(f"Stockfish analysis completed: {stockfish_analysis}")
        
        print("Starting Gemini analysis...")
        # Get Gemini analysis
        gemini_analysis = analyze_with_gemini(fen)
        print(f"Gemini analysis completed, length: {len(gemini_analysis)} characters")
        print(f"First 100 chars: {gemini_analysis[:100] if gemini_analysis else 'None'}")
        
        response_data = {
            "fen": fen,
            "stockfish": stockfish_analysis,
            "gemini": gemini_analysis
        }
        print("Preparing JSON response")
        
        return jsonify(response_data)
    
    except Exception as e:
        error_msg = f"Error in analyze_position endpoint: {str(e)}"
        print(f"❌ ENDPOINT ERROR: {error_msg}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": error_msg}), 500

@app.route('/api/get_stockfish_move', methods=['POST'])
def get_stockfish_move():
    """Get best move from Stockfish for a given position"""
    data = request.json
    fen = data.get('fen', '')
    
    if not fen:
        return jsonify({"error": "FEN position required"}), 400
    
    try:
        stockfish.set_fen_position(fen)
        best_move = stockfish.get_best_move()
        
        return jsonify({
            "best_move": best_move
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat_analysis', methods=['POST'])
def chat_analysis():
    """Get analysis or advice based on a chat question about a position"""
    data = request.json
    fen = data.get('fen', '')
    question = data.get('question', '')
    previous_moves = data.get('previous_moves', '')
    
    if not fen or not question:
        print("ERROR: FEN position and question are required")
        return jsonify({"error": "FEN position and question required"}), 400
    
    try:
        if gemini_model is None:
            print("ERROR: Gemini model is not initialized")
            return jsonify({"error": "Gemini API not configured"}), 500
        
        # Format the prompt for Gemini

        prompt = ""
            
        prompt += f"""
THE USER IS ASKING YOU A CHESS QUESTION. PLEASE RESPOND IN THE FOLLOWING WAY:

You are “The Coach”—a respectful, insightful, and encouraging chess instructor dedicated to helping players improve with thoughtful, constructive feedback.

PREVIOUS MOVES: {previous_moves}
POSITION (FEN): {fen}
THE USER'S QUESTION: {question}

Please analyze the position and respond with:

    Clear Evaluation
    Offer a balanced and professional assessment of the position. Identify which side is better and why, using clear reasoning, without discouraging the user.

    Educational Feedback
    If any inaccuracies or mistakes were made in the previous moves, gently point them out. Treat each as a valuable opportunity to learn, not a failure. Keep your language positive, respectful, and helpful.

    Strategic and Tactical Advice
    Suggest logical next steps and practical plans for the side to move. Keep your suggestions clear and grounded in good principles, and explain why each plan works.

    Supportive Summary
    Finish with an encouraging note—regardless of how strong or weak the position is. Reinforce that chess is a journey and every position teaches something valuable. Focus on growth, learning, and confidence.
        """
    
        # prompt = f"""Chess position (FEN: {fen})
        
        # As a chess grandmaster, I need your help analyzing this position.
        
        # {question}

        # """
        print(f"Prompt created, length: {len(prompt)} characters")
        answer = analyze_with_gemini(fen, previous_moves)
        print('XXXX')
        print(answer)
        print('XXXX')
        # if previous_moves:
        #     prompt += f"\n\nFor context, these are the last few moves: {previous_moves}"
            
        # prompt += """
        # Please provide specific, actionable advice about this position. 
        # Focus directly on answering the question while giving helpful chess insights.
        # """
        
        # # Generate response from Gemini with the same configuration as analyze_with_gemini
        # generation_config = {
        #     "temperature": 0.7,
        #     "top_p": 0.95,
        #     "top_k": 40,
        #     "max_output_tokens": 1024,
        # }
        
        # safety_settings = [
        #     {
        #         "category": "HARM_CATEGORY_HARASSMENT",
        #         "threshold": "ALLOW_ALL"
        #     },
        #     {
        #         "category": "HARM_CATEGORY_HATE_SPEECH",
        #         "threshold": "ALLOW_ALL"
        #     },
        #     {
        #         "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        #         "threshold": "ALLOW_ALL"
        #     },
        #     {
        #         "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        #         "threshold": "ALLOW_ALL"
        #     }
        # ]
        
        # response = gemini_model.generate_content(
        #     prompt,
        #     generation_config=generation_config,
        #     safety_settings=safety_settings
        # )
        
        # Extract the text
        # if hasattr(response, 'text'):
        #     analysis = response.text
        # elif isinstance(response, dict) and 'candidates' in response:
        #     analysis = response['candidates'][0]['content']['parts'][0]['text']
        # else:
        #     analysis = str(response)
        
        return jsonify({
            "response": answer
        })
    
    except Exception as e:
        error_msg = f"Error in chat analysis: {str(e)}"
        print(error_msg)
        return jsonify({"error": error_msg}), 500

@app.route('/api/test_gemini', methods=['GET'])
def test_gemini():
    """Test endpoint to verify Gemini API connectivity"""
    print("\n=== TEST GEMINI ENDPOINT CALLED ===")
    
    if gemini_model is None:
        print("❌ ERROR: Gemini model is not initialized")
        return jsonify({
            "status": "error",
            "message": "Gemini model not initialized. Check your API key."
        }), 500
    
    try:
        print("Creating simple test prompt for Gemini...")
        # Simple test prompt
        test_prompt = "Please respond with 'Gemini API is working correctly'"
        print(f"Test prompt: {test_prompt}")
        
        print("🔄 Sending test request to Gemini API...")
        response = gemini_model.generate_content(test_prompt)
        print("✅ Received response from Gemini API")
        print(f"Response type: {type(response)}")
        
        if hasattr(response, 'text'):
            print(f"Response has 'text' attribute: {response.text}")
            return jsonify({
                "status": "success",
                "message": "Gemini API connection successful",
                "response": response.text
            })
        else:
            print(f"Response in unexpected format: {response}")
            response_str = str(response)
            print(f"Converted to string: {response_str}")
            return jsonify({
                "status": "partial_success",
                "message": "Received response but in unexpected format",
                "response": response_str
            })
    
    except Exception as e:
        error_msg = f"Failed to connect to Gemini API: {str(e)}"
        print(f"❌ TEST ENDPOINT ERROR: {error_msg}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "message": error_msg
        }), 500

# Add a new endpoint for getting analysis for a specific move
@app.route('/api/get_move_analysis', methods=['POST'])
def get_move_analysis():
    """Get detailed analysis for a specific move in a game"""
    try:
        data = request.json
        fen = data.get('fen', '')
        move_number = data.get('move_number', 0)
        move_color = data.get('move_color', '')
        previous_moves = data.get('previous_moves', '')
        
        if not fen:
            return jsonify({"error": "FEN position required"}), 400
            
        # Get fresh analysis for the position
        stockfish_analysis = analyze_position_with_stockfish(fen)
        
        # Get detailed Gemini analysis for this specific move
        prompt_context = f"Move {move_number} ({move_color})"
        if previous_moves:
            prompt_context += f"\nPrevious moves: {previous_moves}"
            
        gemini_analysis = analyze_with_gemini(fen, prompt_context)
        
        return jsonify({
            "move_number": move_number,
            "move_color": move_color,
            "fen": fen,
            "stockfish": stockfish_analysis,
            "gemini": gemini_analysis,
            "previous_moves": previous_moves
        })
        
    except Exception as e:
        error_msg = f"Error in get_move_analysis: {str(e)}"
        print(f"❌ ERROR: {error_msg}")
        return jsonify({"error": error_msg}), 500
if __name__ == '__main__':
    app.run(debug=True, port=5000)