import { Zap, Bot, BrainCircuit, Network } from 'lucide-react';

interface Props {
  layer: 1 | 2 | 3 | 4;
  large?: boolean;
  subText?: string;
}

export function LayerBadge({ layer, large = false, subText }: Props) {
  const className = `badge badge-layer${layer} ${large ? 'large' : ''}`;
  
  if (layer === 1) {
    return (
      <span className={className}>
        <Zap size={large ? 14 : 14} /> Layer 1{large ? ` · ${subText ?? 'Deterministic Rule'}` : ''}
      </span>
    );
  }
  
  if (layer === 2) {
    return (
      <span className={className}>
        <Bot size={large ? 14 : 14} /> Layer 2{large ? ` · ${subText ?? 'Fine-Tuned Model'}` : ''}
      </span>
    );
  }

  if (layer === 3) {
    return (
      <span className={className}>
        <BrainCircuit size={large ? 14 : 14} /> Layer 3{large ? ` · ${subText ?? 'General LLM'}` : ''}
      </span>
    );
  }

  return (
    <span className={className}>
      <Network size={large ? 14 : 14} /> Layer 4{large ? ` · ${subText ?? 'Ensemble AI'}` : ''}
    </span>
  );
}
