export const modules = [
  { slug: "foundations", label: "Foundations", icon: "layers", title: "Build your programming instincts", description: "Practice conditionals, loops, and patterns with small exercises that make the fundamentals stick.", topics: ["Programming logic", "Pattern programming", "Control flow"] },
  { slug: "code", label: "Code & DSA", icon: "code", title: "Turn algorithms into working code", description: "Explore data structures and algorithms, from hash maps to binary search and stacks.", topics: ["Hash maps", "Binary search", "Stacks"] },
  { slug: "data", label: "Data", icon: "database", title: "Make sense of real data", description: "Query tables, filter DataFrames, and transform arrays across SQL, Pandas, and NumPy.", topics: ["SQL", "Pandas", "NumPy"] },
  { slug: "statistics", label: "Statistics", icon: "chart", title: "Reason from evidence", description: "Build statistical intuition through numerical problems, conceptual questions, and dataset analysis.", topics: ["Descriptive statistics", "Probability", "Outlier detection"] },
  { slug: "big-data", label: "Big Data", icon: "network", title: "Think in distributed systems", description: "Practice grouping, aggregation, and map-reduce patterns with Spark and Python exercises.", topics: ["PySpark", "MapReduce", "Aggregations"] },
  { slug: "ai", label: "AI & ML", icon: "sparkles", title: "Build a foundation in AI", description: "Implement model predictions, classification metrics, and tensor operations.", topics: ["Machine learning", "Deep learning", "Model evaluation"] },
] as const;

export const community = [
  { slug: "daily-sadhana", label: "Daily Sadhana", icon: "flame", title: "Make practice a daily habit", description: "Start with the featured Foundations exercise. Rotating challenges and streak tracking are planned.", topics: ["Featured exercise", "Daily rotation planned", "Streak history planned"] },
  { slug: "arena", label: "Arena", icon: "trophy", title: "Prepare for the Arena", description: "Practice with the Code catalog while timed contests, registration, and ratings are in development.", topics: ["Algorithm practice", "Timed contests planned", "Contest ratings planned"] },
  { slug: "rankings", label: "Maharathi Rankings", icon: "target", title: "The Maharathi rank ladder", description: "Explore the six ranks and their initial XP thresholds. XP awards and ranked accounts are planned.", topics: [] },
  { slug: "badges", label: "Veer Badges", icon: "award", title: "Milestones worth earning", description: "Preview the first milestones. Badge awards will go live with verified progress tracking.", topics: ["First solve", "Seven-day streak", "First contest"] },
  { slug: "vidya-paths", label: "Vidya Paths", icon: "route", title: "Learn in a deliberate order", description: "Preview the Foundations path from conditionals to loops and patterns. Enrollment and saved progress are planned.", topics: ["1. Conditionals", "2. Loops", "3. Patterns"] },
  { slug: "progress-insights", label: "Progress Insights", icon: "activity", title: "See your practice over time", description: "This preview uses demo activity. Personal history will appear when submissions and account tracking are available.", topics: [] },
] as const;

export const ranks = [
  ["Shishya", 0], ["Sadhak", 500], ["Kushal", 1500], ["Nipuna", 3500], ["Acharya", 7500], ["Maharathi", 15000],
] as const;
