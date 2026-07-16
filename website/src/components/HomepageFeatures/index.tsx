import type {ReactNode} from 'react';
import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

type FeatureItem = {
  title: string;
  imgSrc: string;
  description: ReactNode;
};

const FeatureList: FeatureItem[] = [
  {
    title: 'Deterministic Blast Radius',
    imgSrc: 'img/dark_mode_radial.png',
    description: (
      <>
        Map the transitive blast radius of any symbol to arbitrary depth. Know exactly what will break <strong>before</strong> you make the edit.
      </>
    ),
  },
  {
    title: 'Zero LLM Calls',
    imgSrc: 'img/horizontal_tree.png',
    description: (
      <>
        Pure static analysis: Tree-sitter AST parsing into PostgreSQL. No vector index, no embedding cost, no hallucination — just deterministic facts.
      </>
    ),
  },
  {
    title: 'Native MCP Server',
    imgSrc: 'img/n3mo_intro.gif',
    description: (
      <>
        Give your AI agents structural memory. N3MO's MCP server lets Cursor, Claude, and Windsurf query the actual code graph in real time.
      </>
    ),
  },
];

function Feature({title, imgSrc, description}: FeatureItem) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center">
        <img src={imgSrc} className={styles.featureImg} alt={title} />
      </div>
      <div className="text--center padding-horiz--md">
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures(): ReactNode {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
