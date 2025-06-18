document.addEventListener("DOMContentLoaded", function () {
    const choices = document.querySelectorAll(".choice");
    const playerChoiceDisplay = document.getElementById("player-choice");
    const computerChoiceDisplay = document.getElementById("computer-choice");
    const winnerDisplay = document.getElementById("winner");
    const playerScoreDisplay = document.getElementById("player-score");
    const computerScoreDisplay = document.getElementById("computer-score");
    const resetButton = document.getElementById("reset-game");

    let playerScore = 0;
    let computerScore = 0;

    choices.forEach(choice => {
        choice.addEventListener("click", function () {
            const playerChoice = this.id;
            const computerChoice = getComputerChoice();

            playerChoiceDisplay.textContent = `You: ${getEmoji(playerChoice)}`;
            computerChoiceDisplay.textContent = `Computer: ${getEmoji(computerChoice)}`;

            const winner = determineWinner(playerChoice, computerChoice);
            winnerDisplay.textContent = winner;

            if (winner === "You win!") {
                playerScore++;
                playerScoreDisplay.textContent = playerScore;
            } else if (winner === "Computer wins!") {
                computerScore++;
                computerScoreDisplay.textContent = computerScore;
            }
        });
    });

    resetButton.addEventListener("click", function () {
        playerScore = 0;
        computerScore = 0;
        playerScoreDisplay.textContent = "0";
        computerScoreDisplay.textContent = "0";
        playerChoiceDisplay.textContent = "You: ❓";
        computerChoiceDisplay.textContent = "Computer: ❓";
        winnerDisplay.textContent = "Make your move!";
    });

    function getComputerChoice() {
        const choices = ["rock", "paper", "scissors"];
        return choices[Math.floor(Math.random() * choices.length)];
    }

    function determineWinner(player, computer) {
        if (player === computer) return "It's a tie!";
        if (
            (player === "rock" && computer === "scissors") ||
            (player === "scissors" && computer === "paper") ||
            (player === "paper" && computer === "rock")
        ) {
            return "You win!";
        } else {
            return "Computer wins!";
        }
    }

    function getEmoji(choice) {
        return choice === "rock" ? "✊" :
               choice === "paper" ? "✋" :
               choice === "scissors" ? "✌️" : "❓";
    }
});
