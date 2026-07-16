import type {ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import HomepageFeatures from '@site/src/components/HomepageFeatures';
import Heading from '@theme/Heading';

import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <img
          src="img/n3mo_logo.svg"
          alt="N3MO Logo"
          style={{width: 80, height: 80, marginBottom: '1.5rem'}}
        />
        <Heading as="h1" className="hero__title">
          {siteConfig.title}
        </Heading>
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <p style={{
          opacity: 0.5,
          fontSize: '0.9rem',
          marginBottom: '2rem',
          color: '#94a3b8',
          fontFamily: "'JetBrains Mono', monospace",
          letterSpacing: '0.02em',
        }}>
          Parse once. Query forever. Know exactly what breaks before it does.
        </p>
        <div className={styles.buttons}>
          <Link
            className="button button--secondary button--lg"
            to="/docs/introduction">
            Get Started →
          </Link>
        </div>
      </div>
    </header>
  );
}

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title="Structural Code Intelligence Layer"
      description="N3MO transforms source code into a queryable knowledge graph for search, impact analysis, and AI-powered development.">
      <HomepageHeader />
      <main>
        <HomepageFeatures />
      </main>
    </Layout>
  );
}
