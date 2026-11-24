import Link from "next/link";
import { ArrowUpRight, ChartNoAxesCombined, Code2, Sparkles, Trophy } from "lucide-react";
import { AuthForm } from "@/components/auth-form";

export const metadata = { title: "Sign in or create account" };

export default function AuthPage() {
  return <div className="auth-experience">
    <header className="auth-site-header">
      <Link href="/" className="auth-site-brand" aria-label="EKLAVYA home">
        <span className="auth-site-brand-mark"><Code2 size={21} strokeWidth={2.4}/></span>
        <span>EKLAVYA</span>
      </Link>
      <Link href="/problems" className="auth-guest-link">Explore problems <ArrowUpRight size={16}/></Link>
    </header>

    <div className="auth-experience-grid">
      <section className="auth-story" aria-labelledby="auth-story-title">
        <div className="auth-story-aura" aria-hidden="true"/>
        <div className="auth-story-inner">
          <div className="auth-story-eyebrow"><span className="auth-story-signal"/> YOUR SPACE TO GROW</div>
          <h1 id="auth-story-title">One challenge at a time. <span>Real progress over time.</span></h1>
          <p className="auth-story-description">
            A focused home for programming, data science and AI. Build skills through practice, see what you have mastered, and keep moving forward.
          </p>

          <div className="auth-showcase" aria-hidden="true">
            <div className="auth-showcase-toolbar">
              <div className="auth-showcase-dots"><i/><i/><i/></div>
              <span>practice / python</span>
              <span className="auth-showcase-language">PYTHON</span>
            </div>
            <div className="auth-showcase-code">
              <div><span className="auth-line-number">01</span><span className="auth-code-comment"># Small steps become strong foundations.</span></div>
              <div><span className="auth-line-number">02</span><span><span className="auth-code-keyword">def</span> <span className="auth-code-function">keep_learning</span>(skill):</span></div>
              <div><span className="auth-line-number">03</span><span className="auth-indent"><span className="auth-code-keyword">return</span> skill + <span className="auth-code-string">" + practice"</span></span></div>
              <div><span className="auth-line-number">04</span><span/></div>
              <div><span className="auth-line-number">05</span><span><span className="auth-code-function">print</span>(keep_learning(<span className="auth-code-string">"curiosity"</span>))</span></div>
            </div>
            <div className="auth-showcase-output"><span className="auth-output-dot"/><span>Ready when you are</span><span className="auth-output-check">✓</span></div>
          </div>

          <div className="auth-story-benefits">
            <div><span className="auth-benefit-icon"><Code2 size={17}/></span><span><strong>Practice</strong><small>Hands-on challenges</small></span></div>
            <div><span className="auth-benefit-icon"><ChartNoAxesCombined size={17}/></span><span><strong>Track</strong><small>See your growth</small></span></div>
            <div><span className="auth-benefit-icon"><Trophy size={17}/></span><span><strong>Master</strong><small>Keep building skills</small></span></div>
          </div>
        </div>
      </section>

      <div className="auth-access-column">
        <AuthForm/>
        <p className="auth-access-footnote"><Sparkles size={14}/> Your progress stays connected to your account.</p>
      </div>
    </div>

    <footer className="auth-site-footer"><span>EKLAVYA — Learn. Practice. Master.</span><span>Built for curious minds and consistent practice.</span></footer>
  </div>;
}
