/**
 * Funny-name generator — mirrors backend/raidio/core/names.py.
 * Generation is client-side to avoid a roundtrip.
 */

const ADJECTIVES = [
  "absurd", "adaptable", "adventurous", "brave", "breezy", "brilliant",
  "bouncy", "calm", "capricious", "celestial", "charming", "clumsy",
  "cosmic", "courageous", "curious", "daring", "dazzling", "delightful",
  "dexterous", "dynamic", "eager", "elastic", "electric", "eloquent",
  "enchanted", "energetic", "enigmatic", "enthusiastic", "epic", "euphoric",
  "fearless", "feisty", "ferocious", "fiery", "flexible", "fluffy",
  "foolish", "frantic", "friendly", "frosty", "furious", "fuzzy",
  "gentle", "giddy", "gigantic", "glorious", "glowing", "graceful",
  "grumpy", "gusty", "hasty", "heroic", "hilarious", "hollow",
  "honest", "hungry", "hyperactive", "hysterical", "icy", "imaginary",
  "incredible", "infinite", "invisible", "jagged", "jazzy", "jittery",
  "jolly", "joyful", "juicy", "jumpy", "keen", "kinetic", "knotty",
  "lazy", "legendary", "limber", "lofty", "loud", "luminous",
  "lumpy", "lustrous", "mad", "magical", "magnetic", "magnificent",
  "messy", "mighty", "miniature", "mysterious", "nebulous", "nimble",
  "nostalgic", "novel", "nutty", "obscure", "odd", "optimistic",
  "outrageous", "panicked", "peculiar", "perplexed", "playful", "plucky",
  "polished", "ponderous", "prickly", "prismatic", "proud", "puzzled",
  "quaint", "quirky", "radiant", "rapid", "reckless", "relentless",
  "restless", "ridiculous", "robust", "rowdy", "rustic", "sassy",
  "scattered", "scrappy", "shiny", "shy", "silent", "silly",
  "sleepy", "slick", "slippery", "slow", "smoky", "snazzy",
  "snippy", "snoopy", "soggy", "sparkling", "splendid", "spontaneous",
  "spry", "squishy", "stealthy", "sturdy", "subtle", "sudden",
  "sunny", "superb", "supersonic", "swanky", "swift", "tangled",
  "tenacious", "thunderous", "tiny", "tough", "turbulent", "twisted",
  "unpredictable", "velvety", "vibrant", "vicious", "volatile", "wacky",
  "wandering", "warm", "whimsical", "wicked", "wiggly", "wild",
  "wobbly", "wonderful", "wooden", "wrathful", "wry", "yawning",
  "youthful", "zealous", "zesty", "zigzagging", "zippy", "zooming",
];

const SCIENTISTS = [
  "Archimedes", "Aristotle", "Bohr", "Boltzmann", "Brahe", "Cauchy",
  "Curie", "Darwin", "Doppler", "Einstein", "Euclid", "Euler",
  "Faraday", "Fermat", "Fermi", "Feynman", "Fourier", "Galileo",
  "Gauss", "Gibbs", "Hawking", "Heisenberg", "Hertz", "Hubble",
  "Huygens", "Joule", "Kepler", "Kirchhoff", "Lagrange", "Laplace",
  "Leibniz", "Lovelace", "Maxwell", "Mendel", "Mendeleev", "Navier",
  "Neumann", "Newton", "Noether", "Ohm", "Planck", "Poincare",
  "Ptolemy", "Pythagoras", "Ramanujan", "Rutherford", "Schrödinger",
  "Shannon", "Siemens", "Socrates", "Tesla", "Thomson", "Turing",
  "Volta", "Watt", "Weber", "Wien", "Wright", "Young",
];

function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

export function generateName(): string {
  return `${pick(ADJECTIVES)}_${pick(SCIENTISTS)}`;
}
