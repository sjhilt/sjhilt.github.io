document.addEventListener("DOMContentLoaded", () => {
    const board = document.querySelector(".board");
    const cells = document.querySelectorAll(".cell");
    const statusText = document.querySelector(".status");
    const restartBtn = document.getElementById("restart");
    const twoPlayerBtn = document.getElementById("twoPlayer");
    const singlePlayerBtn = document.getElementById("singlePlayer");

    let boardState = ["", "", "", "", "", "", "", "", ""];
    let currentPlayer = "X";
    let gameActive = false;
    let singlePlayerMode = false;

    const winningCombos = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8], 
        [0, 3, 6], [1, 4, 7], [2, 5, 8], 
        [0, 4, 8], [2, 4, 6] 
    ];

    function startGame(mode) {
        gameActive = true;
        singlePlayerMode = mode === "single";
        boardState.fill("");
        currentPlayer = "X";
        cells.forEach(cell => {
            cell.textContent = "";
            cell.addEventListener("click", handleMove, { once: true });
        });
        statusText.textContent = "Player X's turn";
        restartBtn.style.display = "block";
    }

    function handleMove(event) {
        const cell = event.target;
        const index = cell.getAttribute("data-index");

        if (boardState[index] !== "" || !gameActive) return;

        boardState[index] = currentPlayer;
        cell.textContent = currentPlayer;

        if (checkWinner()) {
            statusText.textContent = `Player ${currentPlayer} wins!`;
            gameActive = false;
            return;
        }

        if (boardState.every(cell => cell !== "")) {
            statusText.textContent = "It's a draw!";
            gameActive = false;
            return;
        }

        currentPlayer = currentPlayer === "X" ? "O" : "X";
        statusText.textContent = `Player ${currentPlayer}'s turn`;

        if (singlePlayerMode && currentPlayer === "O") {
            setTimeout(aiMove, 500);
        }
    }

    function aiMove() {
        let mistakeChance = 0.2; // 20% chance of making a mistake
        let bestMove = getBestMove();
    
        if (Math.random() < mistakeChance) {
            // Choose a random valid move instead of the best move
            let availableMoves = boardState
                .map((cell, index) => (cell === "" ? index : null))
                .filter(index => index !== null);
            if (availableMoves.length > 0) {
                bestMove = availableMoves[Math.floor(Math.random() * availableMoves.length)];
            }
        }
    
        if (bestMove !== null) {
            let aiCell = document.querySelector(`.cell[data-index='${bestMove}']`);
            aiCell.click();
        }
    }

    function getBestMove() {
        let bestScore = -Infinity;
        let move = null;

        for (let i = 0; i < boardState.length; i++) {
            if (boardState[i] === "") {
                boardState[i] = "O";
                let score = minimax(boardState, 0, false);
                boardState[i] = "";

                if (score > bestScore) {
                    bestScore = score;
                    move = i;
                }
            }
        }
        return move;
    }

    function minimax(board, depth, isMaximizing) {
        let result = evaluate(board);
        if (result !== 0) return result;
        if (board.every(cell => cell !== "")) return 0; // Draw

        if (isMaximizing) {
            let bestScore = -Infinity;
            for (let i = 0; i < board.length; i++) {
                if (board[i] === "") {
                    board[i] = "O";
                    let score = minimax(board, depth + 1, false);
                    board[i] = "";
                    bestScore = Math.max(score, bestScore);
                }
            }
            return bestScore;
        } else {
            let bestScore = Infinity;
            for (let i = 0; i < board.length; i++) {
                if (board[i] === "") {
                    board[i] = "X";
                    let score = minimax(board, depth + 1, true);
                    board[i] = "";
                    bestScore = Math.min(score, bestScore);
                }
            }
            return bestScore;
        }
    }

    function evaluate(board) {
        for (let combo of winningCombos) {
            const [a, b, c] = combo;
            if (board[a] === "O" && board[b] === "O" && board[c] === "O") return 10;
            if (board[a] === "X" && board[b] === "X" && board[c] === "X") return -10;
        }
        return 0;
    }

    function checkWinner() {
        return winningCombos.some(combo => {
            const [a, b, c] = combo;
            return boardState[a] !== "" && boardState[a] === boardState[b] && boardState[a] === boardState[c];
        });
    }

    restartBtn.addEventListener("click", () => startGame(singlePlayerMode ? "single" : "multi"));
    twoPlayerBtn.addEventListener("click", () => startGame("multi"));
    singlePlayerBtn.addEventListener("click", () => startGame("single"));
});
