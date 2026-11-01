import { AnalyzeContractView } from './analyzeContract/AnalyzeContractView';
import { useAnalyzeContractController } from './analyzeContract/useAnalyzeContractController';

export default function AnalyzeContract() {
  const controller = useAnalyzeContractController();
  return <AnalyzeContractView {...controller} />;
}
