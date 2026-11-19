export const modules = [
  { slug: "foundations", label: "Foundations", icon: "layers", title: "Build your programming instincts", description: "Practice conditionals, loops, and patterns with small exercises that make the fundamentals stick.", topics: ["Programming logic", "Pattern programming", "Control flow"] },
  { slug: "code", label: "Code & DSA", icon: "code", title: "Turn algorithms into working code", description: "Explore data structures and algorithms, from hash maps to binary search and stacks.", topics: ["Hash maps", "Binary search", "Stacks"] },
  { slug: "data", label: "Data", icon: "database", title: "Make sense of real data", description: "Query tables, filter DataFrames, and transform arrays across SQL, Pandas, and NumPy.", topics: ["SQL", "Pandas", "NumPy"] },
  { slug: "statistics", label: "Statistics", icon: "chart", title: "Reason from evidence", description: "Build statistical intuition through numerical problems, conceptual questions, and dataset analysis.", topics: ["Descriptive statistics", "Probability", "Outlier detection"] },
  { slug: "big-data", label: "Big Data", icon: "network", title: "Think in distributed systems", description: "Practice grouping, aggregation, and map-reduce patterns with Spark and Python exercises.", topics: ["PySpark", "MapReduce", "Aggregations"] },
  { slug: "ai", label: "AI & ML", icon: "sparkles", title: "Build a foundation in AI", description: "Implement model predictions, classification metrics, and tensor operations.", topics: ["Machine learning", "Deep learning", "Model evaluation"] },
] as const;

export const community = [
  { slug: "daily-sadhana", label: "Daily Sadhana", icon: "flame", title: "Make practice a daily habit", description: "Solve today’s UTC challenge, earn bonus XP, and build a verified practice streak.", topics: ["Daily rotation", "Bonus XP", "Streak history"] },
  { slug: "arena", label: "Arena", icon: "trophy", title: "Compete in the Arena", description: "Register for timed contests, solve under pressure, and build your contest rating.", topics: [] },
  { slug: "rankings", label: "Maharathi Rankings", icon: "target", title: "The Maharathi rank ladder", description: "See the live leaderboard and progress through six ranks using verified XP.", topics: [] },
  { slug: "badges", label: "Veer Badges", icon: "award", title: "Milestones worth earning", description: "Earn badges for first solves, specialist tracks, streaks, and Arena participation.", topics: ["First solve", "Seven-day streak", "First contest"] },
  { slug: "vidya-paths", label: "Vidya Paths", icon: "route", title: "Learn in a deliberate order", description: "Enroll in structured paths and advance as the judge verifies each required solution.", topics: ["Structured sequences", "Milestones", "Verified progress"] },
  { slug: "progress-insights", label: "Progress Insights", icon: "activity", title: "See your practice over time", description: "Review verified activity, solved topics, and recent XP progress.", topics: [] },
] as const;

export const ranks = [
  ["Shishya", 0], ["Sadhak", 500], ["Kushal", 1500], ["Nipuna", 3500], ["Acharya", 7500], ["Maharathi", 15000],
] as const;
