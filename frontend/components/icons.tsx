import { Activity, Award, Braces, ChartNoAxesColumnIncreasing, Database, Flame, Layers, Network, Route, Sparkles, Target, Trophy } from "lucide-react";

const icons = {
  activity: Activity, award: Award, code: Braces, chart: ChartNoAxesColumnIncreasing,
  database: Database, flame: Flame, layers: Layers, network: Network, route: Route,
  sparkles: Sparkles, target: Target, trophy: Trophy,
};

export function ModuleIcon({ name, size = 19 }: { name: keyof typeof icons; size?: number }) {
  const Icon = icons[name];
  return <Icon size={size} aria-hidden="true" />;
}
