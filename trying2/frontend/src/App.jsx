import React, { useState, useEffect, useRef } from "react";
import { Chess } from "chess.js";
import { Chessboard } from "react-chessboard";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

function App() {
  const [game, setGame] = useState(new Chess());
  const [fen, setFen] = useState("start");
  const [pgn, setPgn] = useState("");
  const [mode, setMode] = useState("analyze"); // 'analyze' or 'play'
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [chatHistory, setChatHistory] = useState([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [gameHistory, setGameHistory] = useState([]);
  const [currentMoveIndex, setCurrentMoveIndex] = useState(-1);
  const [moveAnalysis, setMoveAnalysis] = useState(null);
  const starFieldRef = useRef(null);
  const starsIntervalRef = useRef(null);

  const API_URL = "http://localhost:5000/api";

  // Star field functions
  const addStars = (starFieldWidth, starFieldHeight, noOfStars) => {
    const starField = starFieldRef.current;
    if (!starField) return;
    while (starField.firstChild) {
      starField.firstChild.remove();
    }
    const numberOfStars = noOfStars;
    for (let i = 0; i < numberOfStars; i++) {
      const star = document.createElement("div");
      star.className = "star";
      const topOffset = Math.floor(Math.random() * starFieldHeight + 1);
      const leftOffset = Math.floor(Math.random() * starFieldWidth + 1);
      star.style.top = `${topOffset}px`;
      star.style.left = `${leftOffset}px`;
      star.style.position = "absolute";
      starField.appendChild(star);
    }
  };

  const animateStars = (starFieldWidth, speed) => {
    const starField = starFieldRef.current;
    if (!starField) return;
    const stars = starField.childNodes;

    const getStarColor = (index) => {
      if (index % 8 === 0) return "red";
      else if (index % 10 === 0) return "yellow";
      else if (index % 17 === 0) return "blue";
      else return "white";
    };

    const getStarDistance = (index) => {
      if (index % 6 === 0) return "";
      else if (index % 9 === 0) return "near";
      else if (index % 2 === 0) return "far";
      else return "";
    };

    const getStarRelativeSpeed = (index) => {
      if (index % 6 === 0) return 1;
      else if (index % 9 === 0) return 2;
      else if (index % 2 === 0) return -1;
      else return 0;
    };

    if (starsIntervalRef.current) {
      clearInterval(starsIntervalRef.current);
    }

    starsIntervalRef.current = setInterval(() => {
      for (let i = 1; i < stars.length; i++) {
        const star = stars[i];
        star.className = `star ${getStarColor(i)} ${getStarDistance(i)}`;
        let currentLeft = parseInt(star.style.left, 10);
        const leftChangeAmount = speed + getStarRelativeSpeed(i);
        let leftDiff =
          currentLeft - leftChangeAmount < 0
            ? currentLeft - leftChangeAmount + starFieldWidth
            : currentLeft - leftChangeAmount;
        star.style.left = `${leftDiff}px`;
      }
    }, 20);
  };

  // Initialize and update star field
  useEffect(() => {
    const updateStarField = () => {
      const starFieldWidth = window.innerWidth;
      const starFieldHeight = window.innerHeight;
      addStars(starFieldWidth, starFieldHeight, 50);
      animateStars(starFieldWidth, 2);
    };

    updateStarField();

    window.addEventListener("resize", updateStarField);

    return () => {
      window.removeEventListener("resize", updateStarField);
      if (starsIntervalRef.current) {
        clearInterval(starsIntervalRef.current);
      }
    };
  }, []);

  // Reset the board and state
  const resetGame = () => {
    const newGame = new Chess();
    setGame(newGame);
    setFen(newGame.fen());
    setAnalysis(null);
    setChatHistory([]);
    setMoveAnalysis(null);
    setGameHistory([]);
    setCurrentMoveIndex(-1);
  };

  // Handle piece movement
  const onDrop = (sourceSquare, targetSquare) => {
    try {
      const move = game.move({
        from: sourceSquare,
        to: targetSquare,
        promotion: "q",
      });

      if (move === null) return false;

      setFen(game.fen());

      if (mode === "play") {
        makeStockfishMove();
      } else {
        analyzeCurrentPosition();
      }

      return true;
    } catch (error) {
      console.error("Move error:", error);
      return false;
    }
  };

  // Make Stockfish move
  const makeStockfishMove = async () => {
    try {
      setLoading(true);
      const response = await axios.post(`${API_URL}/get_stockfish_move`, {
        fen: game.fen(),
      });

      const bestMove = response.data.best_move;
      if (bestMove) {
        game.move(bestMove, { sloppy: true });
        setFen(game.fen());
      }
      setLoading(false);
    } catch (error) {
      console.error("Stockfish move error:", error);
      setLoading(false);
    }
  };

  // Analyze the current position
  const analyzeCurrentPosition = async () => {
    try {
      setAnalyzing(true);

      const history = game.history({ verbose: true });
      const previousMoves =
        history.length > 0
          ? history
              .slice(Math.max(0, history.length - 5))
              .map((m) => `${m.from}${m.to}`)
              .join(" ")
          : "";

      const response = await axios.post(`${API_URL}/analyze_position`, {
        fen: game.fen(),
        previous_moves: previousMoves,
      });

      setAnalysis(response.data);
      setAnalyzing(false);
    } catch (error) {
      console.error("Analysis error:", error);
      setAnalyzing(false);
    }
  };

  // Navigate to a specific move and fetch analysis
  const goToMove = async (index) => {
    const newGame = new Chess();

    if (index >= 0 && index < gameHistory.length) {
      for (let i = 0; i <= index; i++) {
        newGame.move(gameHistory[i]);
      }
    }

    setGame(newGame);
    setFen(newGame.fen());
    setCurrentMoveIndex(index);

    if (index >= 0 && gameHistory.length > 0) {
      try {
        setAnalyzing(true);
        const history = newGame.history({ verbose: true });
        const previousMoves =
          history.length > 0
            ? history
                .slice(Math.max(0, history.length - 5))
                .map((m) => `${m.from}${m.to}`)
                .join(" ")
            : "";
        const moveNumber = Math.floor(index / 2) + 1;
        const moveColor = index % 2 === 0 ? "White" : "Black";

        const response = await axios.post(`${API_URL}/get_move_analysis`, {
          fen: newGame.fen(),
          move_number: moveNumber,
          move_color: moveColor,
          previous_moves: previousMoves,
        });

        setMoveAnalysis(response.data);
      } catch (error) {
        console.error("Move analysis error:", error);
        setMoveAnalysis({ error: "Failed to fetch move analysis" });
      } finally {
        setAnalyzing(false);
      }
    } else {
      setMoveAnalysis(null);
    }
  };

  // Analyze PGN
  const analyzePGN = async () => {
    if (!pgn.trim()) {
      alert("Please enter PGN data");
      return;
    }

    try {
      setLoading(true);
      const response = await axios.post(`${API_URL}/analyze_pgn`, {
        pgn: pgn,
      });

      const newGame = new Chess();
      try {
        newGame.loadPgn(pgn);
        const history = newGame.history();
        setGameHistory(history);
        setGame(newGame);
        setFen(newGame.fen());
        setCurrentMoveIndex(history.length - 1);
      } catch (pgnError) {
        console.error("PGN parse error:", pgnError);
      }

      setAnalysis(response.data);
      setLoading(false);
    } catch (error) {
      console.error("PGN analysis error:", error);
      setLoading(false);
    }
  };

  // Send a chat message to get analysis
  const sendChatMessage = async () => {
    if (!chatInput.trim()) return;

    const userMessage = chatInput;
    setChatInput("");

    setChatHistory((prev) => [...prev, { role: "user", content: userMessage }]);

    try {
      const history = game.history({ verbose: true });
      const previousMoves =
        history.length > 0
          ? history
              .slice(Math.max(0, history.length - 5))
              .map((m) => `${m.from}${m.to}`)
              .join(" ")
          : "";

      const response = await axios.post(`${API_URL}/chat_analysis`, {
        fen: game.fen(),
        question: userMessage,
        previous_moves: previousMoves,
      });

      setChatHistory((prev) => [
        ...prev,
        { role: "assistant", content: response.data.response },
      ]);
    } catch (error) {
      console.error("Chat analysis error:", error);
      setChatHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I encountered an error analyzing this position.",
        },
      ]);
    }
  };

  // Format evaluation for display
  const formatEvaluation = (evaluation) => {
    if (!evaluation) return "N/A";

    if (evaluation.type === "cp") {
      let value = evaluation.value / 100;
      return `${value > 0 ? "+" : ""}${value.toFixed(2)}`;
    } else if (evaluation.type === "mate") {
      return `Mate in ${evaluation.value}`;
    }

    return JSON.stringify(evaluation);
  };

  return (
    <div className="relative min-h-screen">
      <div
        id="star-field"
        ref={starFieldRef}
        className="absolute inset-0 z-0"
      ></div>
      <div className="relative z-10 max-w-6xl mx-auto p-4 sm:p-6">
        <header className="bg-gradient-to-b from-gray-800 to-gray-900 p-4 rounded-lg shadow-lg mb-6">
          <h1 className="text-2xl sm:text-3xl text-[#eeeed2] font-bold">
            Chaturanga
          </h1>
          <div className="flex gap-3 mt-3">
            <button
              className={`px-4 py-2 rounded-md border border-[#769656] text-gray-200 bg-gray-700 hover:bg-[#769656] hover:text-white transition-all ${
                mode === "analyze" ? "bg-[#769656] font-semibold" : ""
              }`}
              onClick={() => setMode("analyze")}
            >
              Analyze Mode
            </button>
            <button
              className={`px-4 py-2 rounded-md border border-[#769656] text-gray-200 bg-gray-700 hover:bg-[#769656] hover:text-white transition-all ${
                mode === "play" ? "bg-[#769656] font-semibold" : ""
              }`}
              onClick={() => {
                setMode("play");
                resetGame();
              }}
            >
              Play vs Stockfish
            </button>
          </div>
        </header>

        <div className="flex flex-col md:flex-row gap-6">
          <div className="flex-1 min-w-[300px]">
            <Chessboard
              position={fen}
              onPieceDrop={onDrop}
              boardWidth={500}
              areArrowsAllowed={true}
              customDarkSquareStyle={{ backgroundColor: "#769656" }}
              customLightSquareStyle={{ backgroundColor: "#eeeed2" }}
            />
            <div className="flex flex-wrap gap-3 mt-3">
              <button
                className="px-4 py-2 bg-gray-700 text-gray-200 border border-[#769656] rounded-md hover:bg-[#769656] hover:text-white transition-all"
                onClick={resetGame}
              >
                Reset Board
              </button>
              {mode === "play" && (
                <button
                  className={`px-4 py-2 bg-gray-700 text-gray-200 border border-[#769656] rounded-md hover:bg-[#769656] hover:text-white transition-all ${
                    loading || game.isGameOver() ? "opacity-50 cursor-not-allowed" : ""
                  }`}
                  onClick={makeStockfishMove}
                  disabled={loading || game.isGameOver()}
                >
                  {loading ? "Thinking..." : "Get Stockfish Move"}
                </button>
              )}
              {gameHistory.length > 0 && (
                <div className="flex gap-3 mt-3">
                  <button
                    className={`px-3 py-2 bg-gray-700 text-gray-200 border border-[#769656] rounded-md hover:bg-[#769656] hover:text-white transition-all ${
                      currentMoveIndex === -1 ? "opacity-50 cursor-not-allowed" : ""
                    }`}
                    onClick={() => goToMove(-1)}
                    disabled={currentMoveIndex === -1}
                  >
                    ⏮️ Start
                  </button>
                  <button
                    className={`px-3 py-2 bg-gray-700 text-gray-200 border border-[#769656] rounded-md hover:bg-[#769656] hover:text-white transition-all ${
                      currentMoveIndex <= -1 ? "opacity-50 cursor-not-allowed" : ""
                    }`}
                    onClick={() => goToMove(currentMoveIndex - 1)}
                    disabled={currentMoveIndex <= -1}
                  >
                    ⬅️ Previous
                  </button>
                  <button
                    className={`px-3 py-2 bg-gray-700 text-gray-200 border border-[#769656] rounded-md hover:bg-[#769656] hover:text-white transition-all ${
                      currentMoveIndex >= gameHistory.length - 1
                        ? "opacity-50 cursor-not-allowed"
                        : ""
                    }`}
                    onClick={() => goToMove(currentMoveIndex + 1)}
                    disabled={currentMoveIndex >= gameHistory.length - 1}
                  >
                    ➡️ Next
                  </button>
                  <button
                    className={`px-3 py-2 bg-gray-700 text-gray-200 border border-[#769656] rounded-md hover:bg-[#769656] hover:text-white transition-all ${
                      currentMoveIndex === gameHistory.length - 1
                        ? "opacity-50 cursor-not-allowed"
                        : ""
                    }`}
                    onClick={() => goToMove(gameHistory.length - 1)}
                    disabled={currentMoveIndex === gameHistory.length - 1}
                  >
                    ⏭️ End
                  </button>
                </div>
              )}
            </div>
            {gameHistory.length > 0 && (
              <div className="mt-6 p-4 bg-gray-800 rounded-lg shadow-lg">
                <h3 className="text-lg text-[#eeeed2] font-semibold mb-3">Move List</h3>
                <div className="flex flex-wrap gap-2">
                  {gameHistory.map((move, index) => (
                    <span
                      key={index}
                      className={`px-2 py-1 rounded-md bg-gray-700 text-gray-200 cursor-pointer hover:bg-[#769656] hover:text-white transition-all ${
                        index === currentMoveIndex ? "bg-[#769656] font-semibold" : ""
                      }`}
                      onClick={() => goToMove(index)}
                    >
                      {index % 2 === 0 ? `${Math.floor(index / 2 + 1)}.` : ""} {move}{" "}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="flex-1 min-w-[300px] flex flex-col gap-6">
            {mode === "analyze" && (
              <div className="bg-gray-800 p-4 rounded-lg shadow-lg">
                <h3 className="text-lg text-[#eeeed2] font-semibold mb-3">Analyze PGN</h3>
                <textarea
                  placeholder="Paste PGN here..."
                  value={pgn}
                  onChange={(e) => setPgn(e.target.value)}
                  rows={5}
                  className="w-full h-24 bg-gray-700 text-gray-200 border border-gray-600 rounded-md p-3 resize-y"
                />
                <button
                  className={`mt-3 px-4 py-2 bg-gray-700 text-gray-200 border border-[#769656] rounded-md hover:bg-[#769656] hover:text-white transition-all ${
                    loading ? "opacity-50 cursor-not-allowed" : ""
                  }`}
                  onClick={analyzePGN}
                  disabled={loading}
                >
                  {loading ? "Analyzing..." : "Analyze"}
                </button>
              </div>
            )}

            {mode === "analyze" && (
              <div className="bg-gradient-to-b from-gray-800 to-gray-900 rounded-lg p-5 shadow-lg border border-gray-700 max-w-xl w-full min-h-[150px] max-h-[280px] overflow-y-auto">
                <div className="bg-gray-700 p-4 rounded-md border border-gray-600 max-h-full overflow-y-auto">
                  <h3 className="text-lg text-[#eeeed2] font-semibold border-b border-[#769656] pb-2 mb-3">
                    Move Analysis
                  </h3>
                  {analyzing ? (
                    <p className="text-gray-400">Fetching move analysis...</p>
                  ) : moveAnalysis ? (
                    <div>
                      <p className="font-bold text-[#769656] mb-4">
                        Move {moveAnalysis.move_number} ({moveAnalysis.move_color})
                      </p>
                      <div className="mb-5">
                        <h4 className="text-base text-[#eeeed2] font-medium mb-2">Stockfish</h4>
                        <p className="text-sm text-gray-200">
                          Evaluation:{" "}
                          {moveAnalysis.stockfish &&
                            formatEvaluation(moveAnalysis.stockfish.evaluation)}
                        </p>
                        <p className="text-sm text-gray-200">
                          Best move:{" "}
                          {moveAnalysis.stockfish && moveAnalysis.stockfish.best_move}
                        </p>
                      </div>
                      <div className="bg-gray-600 p-3 rounded-md border-l-4 border-[#769656]">
                        <h4 className="text-base text-[#eeeed2] font-medium mb-2">
                          Gemini Analysis
                        </h4>
                        {moveAnalysis.gemini ? (
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                              h1: ({ node, ...props }) => (
                                <h1
                                  className="text-lg text-[#eeeed2] font-semibold my-2"
                                  {...props}
                                />
                              ),
                              h2: ({ node, ...props }) => (
                                <h2
                                  className="text-base text-[#eeeed2] font-medium my-2"
                                  {...props}
                                />
                              ),
                              h3: ({ node, ...props }) => (
                                <h3
                                  className="text-sm text-[#eeeed2] font-medium my-2"
                                  {...props}
                                />
                              ),
                              p: ({ node, ...props }) => (
                                <p
                                  className="text-sm text-gray-200 leading-relaxed my-1"
                                  {...props}
                                />
                              ),
                              ul: ({ node, ...props }) => (
                                <ul
                                  className="my-2 pl-5 list-disc text-sm text-gray-200"
                                  {...props}
                                />
                              ),
                              ol: ({ node, ...props }) => (
                                <ol
                                  className="my-2 pl-5 list-decimal text-sm text-gray-200"
                                  {...props}
                                />
                              ),
                              li: ({ node, ...props }) => <li className="mb-1" {...props} />,
                              strong: ({ node, ...props }) => (
                                <strong className="text-white font-bold" {...props} />
                              ),
                              em: ({ node, ...props }) => (
                                <em className="text-gray-200 italic" {...props} />
                              ),
                              code: ({ node, ...props }) => (
                                <code
                                  className="bg-gray-800 text-[#eeeed2] px-1 py-0.5 rounded-sm font-mono text-xs"
                                  {...props}
                                />
                              ),
                              blockquote: ({ node, ...props }) => (
                                <blockquote
                                  className="border-l-4 border-[#769656] pl-3 my-2 bg-gray-700 text-gray-200"
                                  {...props}
                                />
                              ),
                              table: ({ node, ...props }) => (
                                <table className="border-collapse w-full my-2" {...props} />
                              ),
                              th: ({ node, ...props }) => (
                                <th
                                  className="border border-gray-600 p-2 bg-[#769656] text-white font-semibold text-left"
                                  {...props}
                                />
                              ),
                              td: ({ node, ...props }) => (
                                <td
                                  className="border border-gray-600 p-2 bg-gray-700 text-gray-200"
                                  {...props}
                                />
                              ),
                            }}
                          >
                            {moveAnalysis.gemini}
                          </ReactMarkdown>
                        ) : (
                          <p className="text-sm text-gray-200">No analysis available</p>
                        )}
                      </div>
                    </div>
                  ) : (
                    <p className="text-gray-400">Select a move to see analysis.</p>
                  )}
                </div>
              </div>
            )}

            <div className="bg-gray-800 p-4 rounded-lg shadow-lg">
              <h3 className="text-lg text-[#eeeed2] font-semibold mb-3">Chat with Chaturanga</h3>
              <div className="max-h-48 overflow-y-auto p-3 bg-gray-700 rounded-md mb-3">
                {chatHistory.map((msg, index) => (
                  <div
                    key={index}
                    className={`my-2 ${
                      msg.role === "user"
                        ? "ml-2 bg-[#769656] text-white p-2 rounded-md"
                        : "mr-2 bg-gray-600 text-gray-200 p-2 rounded-md"
                    }`}
                  >
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        p: ({ node, ...props }) => (
                          <p className="text-sm leading-relaxed my-1" {...props} />
                        ),
                        ul: ({ node, ...props }) => (
                          <ul className="my-2 pl-5 list-disc text-sm" {...props} />
                        ),
                        ol: ({ node, ...props }) => (
                          <ol className="my-2 pl-5 list-decimal text-sm" {...props} />
                        ),
                        li: ({ node, ...props }) => <li className="mb-1" {...props} />,
                        strong: ({ node, ...props }) => (
                          <strong className="font-bold" {...props} />
                        ),
                        em: ({ node, ...props }) => <em className="italic" {...props} />,
                        code: ({ node, ...props }) => (
                          <code
                            className="bg-gray-800 text-[#eeeed2] px-1 py-0.5 rounded-sm font-mono text-xs"
                            {...props}
                          />
                        ),
                        blockquote: ({ node, ...props }) => (
                          <blockquote
                            className="border-l-4 border-[#769656] pl-3 my-2 bg-gray-700"
                            {...props}
                          />
                        ),
                        table: ({ node, ...props }) => (
                          <table className="border-collapse w-full my-2" {...props} />
                        ),
                        th: ({ node, ...props }) => (
                          <th
                            className="border border-gray-600 p-2 bg-[#769656] text-white font-semibold text-left"
                            {...props}
                          />
                        ),
                        td: ({ node, ...props }) => (
                          <td
                            className="border border-gray-600 p-2 bg-gray-700"
                            {...props}
                          />
                        ),
                        h1: ({ node, ...props }) => (
                          <h1 className="text-lg font-semibold my-2" {...props} />
                        ),
                        h2: ({ node, ...props }) => (
                          <h2 className="text-base font-medium my-2" {...props} />
                        ),
                        h3: ({ node, ...props }) => (
                          <h3 className="text-sm font-medium my-2" {...props} />
                        ),
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                ))}
              </div>
              <div className="flex gap-3">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Ask about this position..."
                  className="flex-1 bg-gray-700 text-gray-200 border border-gray-600 rounded-md p-2"
                  onKeyPress={(e) => e.key === "Enter" && sendChatMessage()}
                />
                <button
                  className="px-4 py-2 bg-gray-700 text-gray-200 border border-[#769656] rounded-md hover:bg-[#769656] hover:text-white transition-all"
                  onClick={sendChatMessage}
                >
                  Send
                </button>
              </div>
            </div>
          </div>
        </div>

        {game.isGameOver() && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center">
            <div className="bg-gray-800 p-6 rounded-lg shadow-xl text-center">
              <h2 className="text-xl text-[#eeeed2] font-semibold mb-3">Game Over</h2>
              <p className="text-gray-200 mb-5">
                {game.isCheckmate()
                  ? "Checkmate!"
                  : game.isDraw()
                  ? "Draw!"
                  : "Game ended."}
              </p>
              <button
                className="px-4 py-2 bg-gray-700 text-gray-200 border border-[#769656] rounded-md hover:bg-[#769656] hover:text-white transition-all"
                onClick={resetGame}
              >
                New Game
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;