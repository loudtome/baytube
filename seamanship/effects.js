// Purely visual SVG effects: the flying cannonball, the impact explosion,
// and a small helper for building freeze-fill <animate> elements.
// Game state is untouched here — animateCannon reports back via a callback.

var SVG_NS = "http://www.w3.org/2000/svg";

function svgAnimate(el, attr, from, to, dur, begin) {
  var a = document.createElementNS(SVG_NS, "animate");
  a.setAttribute("attributeName", attr);
  if (from !== null) a.setAttribute("from", from);
  a.setAttribute("to", to);
  a.setAttribute("dur", dur + "s");
  if (begin) a.setAttribute("begin", begin + "s");
  a.setAttribute("fill", "freeze");
  el.appendChild(a);
  return a;
}

// A burst of fire, flying sparks/debris, and rising smoke at (x, y).
// Self-cleaning: the whole group is removed once the animation finishes.
function explode(x, y) {
  var svg = document.getElementById("ship-svg");
  var group = document.createElementNS(SVG_NS, "g");
  svg.appendChild(group);

  // Bright central flash
  var flash = document.createElementNS(SVG_NS, "circle");
  flash.setAttribute("cx", x);
  flash.setAttribute("cy", y);
  flash.setAttribute("r", "6");
  flash.setAttribute("fill", "#fffbe6");
  group.appendChild(flash);
  svgAnimate(flash, "r", "6", "22", 0.25);
  svgAnimate(flash, "opacity", "1", "0", 0.3);

  // Expanding fireballs in fiery colors
  var fireColors = ["#ffcf3f", "#ff8c1a", "#ff5722", "#e23b1e"];
  for (var f = 0; f < fireColors.length; f++) {
    var fb = document.createElementNS(SVG_NS, "circle");
    var ox = x + (Math.random() * 12 - 6);
    var oy = y + (Math.random() * 12 - 6);
    fb.setAttribute("cx", ox);
    fb.setAttribute("cy", oy);
    fb.setAttribute("r", "3");
    fb.setAttribute("fill", fireColors[f]);
    fb.setAttribute("opacity", "0.95");
    group.appendChild(fb);
    svgAnimate(fb, "r", "3", String(14 + Math.random() * 12), 0.45, f * 0.03);
    svgAnimate(fb, "opacity", "0.95", "0", 0.5, f * 0.03);
  }

  // Flying sparks / debris
  var sparkColors = ["#ffe08a", "#ff9d3c", "#5a3d24", "#3a3a3a"];
  for (var s = 0; s < 14; s++) {
    var ang = (Math.PI * 2 * s) / 14 + Math.random() * 0.4;
    var dist = 22 + Math.random() * 26;
    var spark = document.createElementNS(SVG_NS, "circle");
    spark.setAttribute("cx", x);
    spark.setAttribute("cy", y);
    spark.setAttribute("r", String(1.2 + Math.random() * 1.8));
    spark.setAttribute("fill", sparkColors[s % sparkColors.length]);
    group.appendChild(spark);
    svgAnimate(spark, "cx", x, String(x + Math.cos(ang) * dist), 0.55);
    svgAnimate(spark, "cy", y, String(y + Math.sin(ang) * dist + 8), 0.55);
    svgAnimate(spark, "opacity", "1", "0", 0.55);
  }

  // Lingering smoke puffs
  for (var m = 0; m < 3; m++) {
    var smoke = document.createElementNS(SVG_NS, "circle");
    smoke.setAttribute("cx", x + (Math.random() * 16 - 8));
    smoke.setAttribute("cy", y - 2 - m * 4);
    smoke.setAttribute("r", "4");
    smoke.setAttribute("fill", "#6b6b6b");
    smoke.setAttribute("opacity", "0.5");
    group.appendChild(smoke);
    svgAnimate(smoke, "r", "4", "16", 0.7, 0.15 + m * 0.05);
    svgAnimate(smoke, "cy", y - 2 - m * 4, String(y - 22 - m * 6), 0.7, 0.15 + m * 0.05);
    svgAnimate(smoke, "opacity", "0.5", "0", 0.7, 0.15 + m * 0.05);
  }

  setTimeout(function () { if (group.parentNode) svg.removeChild(group); }, 900);
}

// Fire a cannonball from (startX, startY) at `target`, then explode on impact
// and knock out the hit part. onImpact(isHullHit) runs after the blast so the
// caller can advance the game (re-deal the cards, or sink the ship).
function animateCannon(startX, startY, target, onImpact) {
  playCannonSound();
  var svg = document.getElementById("ship-svg");
  var ball = document.createElementNS(SVG_NS, "circle");
  ball.setAttribute("cx", startX);
  ball.setAttribute("cy", startY);
  ball.setAttribute("r", "5");
  ball.setAttribute("fill", "#222");
  svg.appendChild(ball);

  svgAnimate(ball, "cx", null, target.x, 0.5);
  svgAnimate(ball, "cy", null, target.y, 0.5);

  setTimeout(function () {
    if (ball.parentNode) svg.removeChild(ball);

    var puff = document.createElementNS(SVG_NS, "circle");
    puff.setAttribute("cx", target.x);
    puff.setAttribute("cy", target.y);
    puff.setAttribute("r", "4");
    puff.setAttribute("fill", "#ffdd88");
    puff.setAttribute("opacity", "0.9");
    svgAnimate(puff, "r", null, "28", 0.4);
    svgAnimate(puff, "opacity", null, "0", 0.4);
    svg.appendChild(puff);
    setTimeout(function () { if (puff.parentNode) svg.removeChild(puff); }, 450);

    explode(target.x, target.y);

    var isHullHit = target.id === "hull" || target.id === "p-hull";
    if (!isHullHit) {
      document.getElementById(target.id).classList.add("destroyed");
    }

    setTimeout(function () { onImpact(isHullHit); }, 500);
  }, 520);
}
