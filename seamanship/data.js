// Question bank, category definitions, and the coordinates of each
// destructible ship part. Pure data — no behaviour lives here.

var QUESTIONS = [
  { cat: "channel", q: "What does a red triangular buoy (nun) mean when you're returning from open water?", choices: ["Keep it on your port side", "Keep it on your starboard side", "It's a hazard marker", "It marks safe water all around"], a: 1 },
  { cat: "channel", q: "When returning from sea, on which side should you keep a green square buoy (can)?", choices: ["Starboard", "Port", "Either side", "Directly ahead"], a: 1 },
  { cat: "channel", q: "A buoy with red and green horizontal bands marks what?", choices: ["A junction or channel split", "A shipwreck", "A no-wake zone", "Safe water in all directions"], a: 0 },
  { cat: "channel", q: "Red and white vertical stripes on a marker indicate:", choices: ["A restricted swimming area", "Safe water / mid-channel", "A junction", "A special feature like a cable"], a: 1 },
  { cat: "channel", q: "A yellow buoy or marker typically indicates:", choices: ["Port side of channel", "Starboard side of channel", "A special feature (anchorage, cable, traffic separation)", "Safe water"], a: 2 },
  { cat: "channel", q: "At night, a green light on a channel marker corresponds to:", choices: ["A red nun", "A green can", "A safe water marker", "A regulatory marker"], a: 1 },
  { cat: "channel", q: "At night, a red light on a channel marker corresponds to:", choices: ["A green can", "A red nun", "A junction marker", "A special mark"], a: 1 },
  { cat: "channel", q: "A quick-flashing white light typically marks:", choices: ["Mid-channel / fairway", "Port side returning", "Starboard side returning", "A hazard to avoid entirely"], a: 0 },
  { cat: "channel", q: "A diamond-shaped marker with an orange border and a symbol usually indicates:", choices: ["Regulatory information (hazard, no-wake, restriction)", "Port side channel", "Starboard side channel", "Safe water"], a: 0 },
  { cat: "channel", q: "Two fixed markers aligned vertically, one behind the other, are called:", choices: ["Junction markers", "Range markers, showing the channel centerline", "Safe water markers", "Regulatory markers"], a: 1 },
  { cat: "channel", q: "What does the phrase \"red, right, returning\" mean?", choices: ["Keep red markers on your right heading out to sea", "Keep red markers on your right when returning from open water", "Red markers are always on the right riverbank", "It refers to sunset navigation"], a: 1 },
  { cat: "rightofway", q: "In general, which vessel has right-of-way: a sailboat under sail or a powerboat under engine?", choices: ["Powerboat", "Sailboat", "Whichever is bigger", "First-come-first-served"], a: 1 },
  { cat: "rightofway", q: "Who is responsible for keeping clear in an overtaking situation?", choices: ["The vessel being overtaken", "The overtaking vessel", "Whichever vessel is under sail", "It doesn't matter"], a: 1 },
  { cat: "rightofway", q: "Two power-driven vessels are approaching head-on. What should each do?", choices: ["Both alter course to starboard (turn right)", "Both alter course to port (turn left)", "The larger vessel holds course", "Both stop engines"], a: 0 },
  { cat: "rightofway", q: "In a crossing situation between two power-driven vessels, who must give way?", choices: ["The vessel on the left", "The vessel that has the other vessel on her own starboard side", "The faster vessel", "The vessel closer to shore"], a: 1 },
  { cat: "rightofway", q: "What should the give-way vessel do?", choices: ["Wait until the last moment to act", "Take early and obvious action to avoid collision", "Speed up to cross first", "Sound five short blasts and continue"], a: 1 },
  { cat: "rightofway", q: "What should the stand-on vessel generally do?", choices: ["Maintain course and speed", "Immediately change course", "Stop engines", "Reverse direction"], a: 0 },
  { cat: "rightofway", q: "A vessel restricted in her ability to maneuver (towing, dredging) generally:", choices: ["Must always give way to smaller boats", "Has priority and should be given a wide berth", "Has no special status", "Only has priority at night"], a: 1 },
  { cat: "rightofway", q: "A vessel not under command (disabled, no steering) generally:", choices: ["Has right-of-way over vessels that can still maneuver", "Must give way to all other vessels", "Has no priority", "Is required to anchor immediately"], a: 0 },
  { cat: "rightofway", q: "A vessel actively fishing with gear deployed generally has right-of-way over:", choices: ["Vessels restricted in their ability to maneuver", "Ordinary power-driven and sailing vessels", "Vessels not under command", "All other vessels with no exceptions"], a: 1 },
  { cat: "rightofway", q: "Which of these generally has the least right-of-way and must give way to almost everyone?", choices: ["A sailing vessel", "A power-driven vessel under normal operation", "A vessel not under command", "A vessel restricted in her ability to maneuver"], a: 1 },
  { cat: "seamanship", q: "How long should your anchor rode be relative to the water depth?", choices: ["Equal to the depth of the water", "About 5 to 7 times the depth of the water (scope)", "10 to 12 times the depth of the water", "It doesn't matter as long as the anchor is heavy"], a: 1 },
  { cat: "seamanship", q: "Why is a leeward shore dangerous?", choices: ["It's downwind, so wind and waves push the boat toward it, risking grounding", "It's always too deep to anchor near", "It has no tidal changes", "It's only dangerous at night"], a: 0 },
  { cat: "seamanship", q: "What should you do if your motorboat runs aground?", choices: ["Gun the throttle forward to power through", "Continue forward slowly to look for deeper water", "Stop the engine, check for damage or injuries, then try to back off along the path you came in on", "Abandon ship immediately"], a: 2 },
  { cat: "seamanship", q: "Which VHF radio channel is designated for distress and emergency calls?", choices: ["Channel 6", "Channel 9", "Channel 13", "Channel 16"], a: 3 },
  { cat: "seamanship", q: "What type of life jacket is required on a motorboat?", choices: ["Any flotation cushion is sufficient, no PFD needed", "A USCG-approved wearable life jacket (Type I, II, III, or V) for each person on board", "Only the operator needs a life jacket", "Inflatable arm floaties for children only"], a: 1 },
  { cat: "seamanship", q: "Which knots are most useful for securing a boat to a dock?", choices: ["Cleat hitch, bowline, and clove hitch", "Sheet bend, timber hitch, and prusik knot", "Just a simple overhand knot", "Square knot and slip knot only"], a: 0 },
  { cat: "seamanship", q: "Which VHF radio channel is used for general, routine boater-to-boater communication?", choices: ["Channel 16", "Channel 68", "Channel 13", "Channel 70"], a: 1 }
];

var CATEGORIES = [
  { key: "channel", label: "Channel marker" },
  { key: "rightofway", label: "Right of way" },
  { key: "seamanship", label: "Seamanship" }
];

var PART_LABELS = ["Foresail", "Aft sail", "Foremast", "Aft mast", "Cabin", "Hull"];

// Impact points for each hit, in SVG coordinates. Order matches the sequence
// in which parts are knocked out (see PART_LABELS / hit counters).
var OUR_TARGETS = [
  { id: "foresail", x: 222, y: 108 },
  { id: "aftsail", x: 144, y: 98 },
  { id: "foremast", x: 200, y: 104 },
  { id: "aftmast", x: 98, y: 94 },
  { id: "wheelhouse", x: 149, y: 128 },
  { id: "hull", x: 150, y: 168 }
];
var PIRATE_TARGETS = [
  { id: "p-foresail", x: 338, y: 108 },
  { id: "p-aftsail", x: 416, y: 98 },
  { id: "p-foremast", x: 360, y: 104 },
  { id: "p-aftmast", x: 462, y: 94 },
  { id: "p-wheelhouse", x: 411, y: 128 },
  { id: "p-hull", x: 410, y: 168 }
];
