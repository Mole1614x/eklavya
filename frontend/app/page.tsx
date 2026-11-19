import { Hero, SkillCards } from "@/components/dashboard";

export default function Home() {
  return (
    <>
      <header className="topbar"><strong>EKLAVYA <span className="crumb">/</span> एकलव्य</strong></header>
      <Hero home />
      <section className="skills"><div className="section-heading"><h2>Explore practice areas</h2></div><SkillCards /></section>
    </>
  );
}
