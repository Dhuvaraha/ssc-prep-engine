import TeachingJourney from '../components/TeachingJourney';
import { percentageJourney } from '../api';

export default function PercentageJourneyPage() {
  return <TeachingJourney title="Successive percentages: name the base" load={percentageJourney}/>;
}
