// Game state, scoreboard/UI rendering, question flow, and win/lose handling.
// Relies on: data.js (question bank + targets), audio.js (sounds),
// effects.js (cannon + explosion visuals).

var state = { score: 0, wrong: 0, pirateHits: 0, locked: false, cards: [], answeredCorrect: [] };

function shuffle(arr) {
  var a = arr.slice();
  for (var i = a.length - 1; i > 0; i--) {
    var j = Math.floor(Math.random() * (i + 1));
    var tmp = a[i]; a[i] = a[j]; a[j] = tmp;
  }
  return a;
}

function updateScoreUI() {
  document.getElementById("score").textContent = state.score;
}

function updateLivesUI() {
  var row = document.getElementById("lives-row");
  row.innerHTML = "";
  for (var i = 0; i < PART_LABELS.length; i++) {
    var chip = document.createElement("div");
    chip.className = "life-chip" + (i < state.wrong ? " gone" : "");
    chip.textContent = PART_LABELS[i];
    row.appendChild(chip);
  }
}

function updatePirateLivesUI() {
  var row = document.getElementById("pirate-lives-row");
  row.innerHTML = "";
  for (var i = 0; i < PART_LABELS.length; i++) {
    var chip = document.createElement("div");
    chip.className = "life-chip pirate" + (i < state.pirateHits ? " gone" : "");
    chip.textContent = PART_LABELS[i];
    row.appendChild(chip);
  }
}

function renderCards() {
  state.cards = CATEGORIES.map(function (cat) {
    var pool = QUESTIONS.filter(function (q) { return q.cat === cat.key && state.answeredCorrect.indexOf(q) === -1; });
    if (pool.length === 0) {
      pool = QUESTIONS.filter(function (q) { return q.cat === cat.key; });
    }
    return pool[Math.floor(Math.random() * pool.length)];
  });
  var grid = document.getElementById("cards-grid");
  grid.classList.remove("disabled", "hidden");
  grid.innerHTML = "";
  CATEGORIES.forEach(function (cat, idx) {
    var chest = document.createElement("div");
    chest.className = "chest";
    chest.innerHTML =
      '<div class="chest-glow"></div>' +
      '<div class="chest-base"><div class="chest-label">' + cat.label + '</div></div>' +
      '<div class="chest-lid"></div>' +
      '<div class="chest-lock"></div>';
    chest.addEventListener("click", function () { handleCardClick(idx, chest); });
    grid.appendChild(chest);
  });
}

function handleCardClick(idx, chestEl) {
  if (state.locked) return;
  state.locked = true;
  ensureAudio();
  chestEl.classList.add("open");
  var grid = document.getElementById("cards-grid");
  grid.classList.add("disabled");
  setTimeout(function () {
    grid.classList.add("hidden");
    showQuestion(state.cards[idx]);
  }, 500);
}

function showQuestion(item) {
  var panel = document.getElementById("question-panel");
  panel.classList.remove("hidden");
  document.getElementById("question-text").textContent = item.q;
  var choicesEl = document.getElementById("choices");
  choicesEl.innerHTML = "";
  item.choices.forEach(function (choiceText, i) {
    var btn = document.createElement("button");
    btn.className = "choice-btn";
    btn.textContent = choiceText;
    btn.addEventListener("click", function () { handleAnswer(i, item, choicesEl); });
    choicesEl.appendChild(btn);
  });
}

function handleAnswer(selected, item, choicesEl) {
  var correctIdx = item.a;
  var btns = choicesEl.querySelectorAll(".choice-btn");
  btns.forEach(function (b) { b.disabled = true; });
  var isCorrect = selected === correctIdx;
  btns[correctIdx].classList.add("correct");
  if (!isCorrect) btns[selected].classList.add("wrong");

  setTimeout(function () {
    document.getElementById("question-panel").classList.add("hidden");
    if (isCorrect) {
      if (state.answeredCorrect.indexOf(item) === -1) {
        state.answeredCorrect.push(item);
      }
      state.score++;
      updateScoreUI();
      state.pirateHits++;
      updatePirateLivesUI();
      fireCannon(246, 128, PIRATE_TARGETS[state.pirateHits - 1]);
    } else {
      state.wrong++;
      updateLivesUI();
      fireCannon(314, 128, OUR_TARGETS[state.wrong - 1]);
    }
  }, 1000);
}

// Fire the cannon, then advance the game once the blast resolves.
function fireCannon(startX, startY, target) {
  animateCannon(startX, startY, target, function (isHullHit) {
    if (isHullHit) {
      sinkShip(target.id === "p-hull");
    } else {
      state.locked = false;
      renderCards();
    }
  });
}

function sinkShip(pirateWon) {
  playSinkSound();
  var groupId = pirateWon ? "pirateShipGroup" : "shipGroup";
  document.getElementById(groupId).classList.add("sinking");
  setTimeout(function () {
    var overlay = document.getElementById("gameover-overlay");
    var heading = document.getElementById("overlay-heading");
    if (pirateWon) {
      heading.textContent = "Victory! The pirate ship has sunk.";
      overlay.classList.add("win");
    } else {
      heading.textContent = "The ship has gone down.";
      overlay.classList.remove("win");
    }
    document.getElementById("final-score-text").textContent = "Final score: " + state.score + " correct answers.";
    overlay.classList.remove("hidden");
  }, 1400);
}

function resetGame() {
  state.score = 0;
  state.wrong = 0;
  state.pirateHits = 0;
  state.locked = false;
  state.answeredCorrect = [];
  updateScoreUI();
  updateLivesUI();
  updatePirateLivesUI();
  ["foresail", "aftsail", "foremast", "aftmast", "wheelhouse", "p-foresail", "p-aftsail", "p-foremast", "p-aftmast", "p-wheelhouse"].forEach(function (id) {
    document.getElementById(id).classList.remove("destroyed");
  });
  document.getElementById("shipGroup").classList.remove("sinking");
  document.getElementById("pirateShipGroup").classList.remove("sinking");
  document.getElementById("gameover-overlay").classList.add("hidden");
  document.getElementById("gameover-overlay").classList.remove("win");
  document.getElementById("question-panel").classList.add("hidden");
  renderCards();
}

document.getElementById("restart-btn").addEventListener("click", resetGame);

updateScoreUI();
updateLivesUI();
updatePirateLivesUI();
renderCards();
