(() => {
  const steps = [
    "Reality is observed.",
    "Observation becomes evidence.",
    "Evidence supports knowledge.",
    "Knowledge informs a decision.",
    "Human approval unlocks execution.",
    "Execution produces verification.",
    "Verification becomes memory."
  ];
  const nodes = [...document.querySelectorAll("[data-step]")];
  const edges = [...document.querySelectorAll("[data-edge]")];
  const narration = document.querySelector("#narration-text");
  const replay = document.querySelector("#replay");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const cycleDuration = 9600;
  const stepDuration = 1200;
  let timer;

  function showStep(index) {
    nodes.forEach((node, nodeIndex) => node.classList.toggle("active", nodeIndex <= index));
    edges.forEach((edge, edgeIndex) => edge.classList.toggle("active", edgeIndex < index));
    narration.textContent = steps[Math.min(index, steps.length - 1)];
  }

  function stop() {
    window.clearInterval(timer);
    timer = undefined;
  }

  function start() {
    stop();
    let index = 0;
    showStep(index);
    if (reduceMotion.matches) {
      showStep(nodes.length - 1);
      return;
    }
    timer = window.setInterval(() => {
      index += 1;
      if (index === nodes.length) {
        index = 0;
      }
      showStep(index);
    }, stepDuration);
  }

  replay.addEventListener("click", start);
  reduceMotion.addEventListener("change", start);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stop();
    else start();
  });
  window.CyberCoreLearn = { showStep, start, stop };
  start();
})();
