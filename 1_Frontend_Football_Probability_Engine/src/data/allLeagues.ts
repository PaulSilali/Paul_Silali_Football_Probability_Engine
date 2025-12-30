/**
 * Complete list of all leagues available on football-data.co.uk
 * 
 * This file contains all leagues that can be downloaded from football-data.co.uk
 * League codes match the database and football-data.co.uk format exactly
 */

export interface League {
  id: string;
  name: string;
  code: string;
  country: string;
  tier: number;
  url: string;
}

export const allLeagues: League[] = [
  // ==========================================================================
  // ENGLAND
  // ==========================================================================
  { id: '1', name: 'Premier League', code: 'E0', country: 'England', tier: 1, url: 'football-data.co.uk/englandm.php' },
  { id: '2', name: 'Championship', code: 'E1', country: 'England', tier: 2, url: 'football-data.co.uk/englandm.php' },
  { id: '3', name: 'League One', code: 'E2', country: 'England', tier: 3, url: 'football-data.co.uk/englandm.php' },
  { id: '4', name: 'League Two', code: 'E3', country: 'England', tier: 4, url: 'football-data.co.uk/englandm.php' },
  
  // ==========================================================================
  // SPAIN
  // ==========================================================================
  { id: '5', name: 'La Liga', code: 'SP1', country: 'Spain', tier: 1, url: 'football-data.co.uk/spainm.php' },
  { id: '6', name: 'La Liga 2', code: 'SP2', country: 'Spain', tier: 2, url: 'football-data.co.uk/spainm.php' },
  
  // ==========================================================================
  // GERMANY
  // ==========================================================================
  { id: '7', name: 'Bundesliga', code: 'D1', country: 'Germany', tier: 1, url: 'football-data.co.uk/germanym.php' },
  { id: '8', name: '2. Bundesliga', code: 'D2', country: 'Germany', tier: 2, url: 'football-data.co.uk/germanym.php' },
  
  // ==========================================================================
  // ITALY
  // ==========================================================================
  { id: '9', name: 'Serie A', code: 'I1', country: 'Italy', tier: 1, url: 'football-data.co.uk/italym.php' },
  { id: '10', name: 'Serie B', code: 'I2', country: 'Italy', tier: 2, url: 'football-data.co.uk/italym.php' },
  
  // ==========================================================================
  // FRANCE
  // ==========================================================================
  { id: '11', name: 'Ligue 1', code: 'F1', country: 'France', tier: 1, url: 'football-data.co.uk/francem.php' },
  { id: '12', name: 'Ligue 2', code: 'F2', country: 'France', tier: 2, url: 'football-data.co.uk/francem.php' },
  
  // ==========================================================================
  // NETHERLANDS
  // ==========================================================================
  { id: '13', name: 'Eredivisie', code: 'N1', country: 'Netherlands', tier: 1, url: 'football-data.co.uk/netherlandsm.php' },
  
  // ==========================================================================
  // PORTUGAL
  // ==========================================================================
  { id: '14', name: 'Primeira Liga', code: 'P1', country: 'Portugal', tier: 1, url: 'football-data.co.uk/portugalm.php' },
  
  // ==========================================================================
  // SCOTLAND
  // ==========================================================================
  { id: '15', name: 'Scottish Premiership', code: 'SC0', country: 'Scotland', tier: 1, url: 'football-data.co.uk/scotlandm.php' },
  { id: '16', name: 'Scottish Championship', code: 'SC1', country: 'Scotland', tier: 2, url: 'football-data.co.uk/scotlandm.php' },
  { id: '17', name: 'Scottish League One', code: 'SC2', country: 'Scotland', tier: 3, url: 'football-data.co.uk/scotlandm.php' },
  { id: '18', name: 'Scottish League Two', code: 'SC3', country: 'Scotland', tier: 4, url: 'football-data.co.uk/scotlandm.php' },
  
  // ==========================================================================
  // BELGIUM
  // ==========================================================================
  { id: '19', name: 'Pro League', code: 'B1', country: 'Belgium', tier: 1, url: 'football-data.co.uk/belgiumm.php' },
  
  // ==========================================================================
  // TURKEY
  // ==========================================================================
  { id: '20', name: 'Super Lig', code: 'T1', country: 'Turkey', tier: 1, url: 'football-data.co.uk/turkeym.php' },
  
  // ==========================================================================
  // GREECE
  // ==========================================================================
  { id: '21', name: 'Super League 1', code: 'G1', country: 'Greece', tier: 1, url: 'football-data.co.uk/greecem.php' },
  
  // ==========================================================================
  // AUSTRIA
  // ==========================================================================
  { id: '22', name: 'Bundesliga', code: 'A1', country: 'Austria', tier: 1, url: 'football-data.co.uk/austriam.php' },
  
  // ==========================================================================
  // SWITZERLAND
  // ==========================================================================
  { id: '23', name: 'Super League', code: 'SW1', country: 'Switzerland', tier: 1, url: 'football-data.co.uk/switzerlandm.php' },
  
  // ==========================================================================
  // DENMARK
  // ==========================================================================
  { id: '24', name: 'Superliga', code: 'DK1', country: 'Denmark', tier: 1, url: 'football-data.co.uk/denmarkm.php' },
  
  // ==========================================================================
  // SWEDEN
  // ==========================================================================
  { id: '25', name: 'Allsvenskan', code: 'SWE1', country: 'Sweden', tier: 1, url: 'football-data.co.uk/swedenm.php' },
  
  // ==========================================================================
  // NORWAY
  // ==========================================================================
  { id: '26', name: 'Eliteserien', code: 'NO1', country: 'Norway', tier: 1, url: 'football-data.co.uk/norwaym.php' },
  
  // ==========================================================================
  // FINLAND
  // ==========================================================================
  { id: '27', name: 'Veikkausliiga', code: 'FIN1', country: 'Finland', tier: 1, url: 'football-data.co.uk/finlandm.php' },
  
  // ==========================================================================
  // POLAND
  // ==========================================================================
  { id: '28', name: 'Ekstraklasa', code: 'PL1', country: 'Poland', tier: 1, url: 'football-data.co.uk/polandm.php' },
  
  // ==========================================================================
  // ROMANIA
  // ==========================================================================
  { id: '29', name: 'Liga 1', code: 'RO1', country: 'Romania', tier: 1, url: 'football-data.co.uk/romaniam.php' },
  
  // ==========================================================================
  // RUSSIA
  // ==========================================================================
  { id: '30', name: 'Premier League', code: 'RUS1', country: 'Russia', tier: 1, url: 'football-data.co.uk/russiam.php' },
  
  // ==========================================================================
  // CZECH REPUBLIC
  // ==========================================================================
  { id: '31', name: 'First League', code: 'CZE1', country: 'Czech Republic', tier: 1, url: 'football-data.co.uk/czechm.php' },
  
  // ==========================================================================
  // CROATIA
  // ==========================================================================
  { id: '32', name: 'Prva HNL', code: 'CRO1', country: 'Croatia', tier: 1, url: 'football-data.co.uk/croatiam.php' },
  
  // ==========================================================================
  // SERBIA
  // ==========================================================================
  { id: '33', name: 'SuperLiga', code: 'SRB1', country: 'Serbia', tier: 1, url: 'football-data.co.uk/serbiam.php' },
  
  // ==========================================================================
  // UKRAINE
  // ==========================================================================
  { id: '34', name: 'Premier League', code: 'UKR1', country: 'Ukraine', tier: 1, url: 'football-data.co.uk/ukrainem.php' },
  
  // ==========================================================================
  // IRELAND
  // ==========================================================================
  { id: '35', name: 'Premier Division', code: 'IRL1', country: 'Ireland', tier: 1, url: 'football-data.co.uk/irelandm.php' },
  
  // ==========================================================================
  // ARGENTINA
  // ==========================================================================
  { id: '36', name: 'Primera Division', code: 'ARG1', country: 'Argentina', tier: 1, url: 'football-data.co.uk/argentinam.php' },
  
  // ==========================================================================
  // BRAZIL
  // ==========================================================================
  { id: '37', name: 'Serie A', code: 'BRA1', country: 'Brazil', tier: 1, url: 'football-data.co.uk/brazilm.php' },
  
  // ==========================================================================
  // MEXICO
  // ==========================================================================
  { id: '38', name: 'Liga MX', code: 'MEX1', country: 'Mexico', tier: 1, url: 'football-data.co.uk/mexicom.php' },
  
  // ==========================================================================
  // USA
  // ==========================================================================
  { id: '39', name: 'Major League Soccer', code: 'USA1', country: 'USA', tier: 1, url: 'football-data.co.uk/usam.php' },
  
  // ==========================================================================
  // CHINA
  // ==========================================================================
  { id: '40', name: 'Super League', code: 'CHN1', country: 'China', tier: 1, url: 'football-data.co.uk/chinam.php' },
  
  // ==========================================================================
  // JAPAN
  // ==========================================================================
  { id: '41', name: 'J-League', code: 'JPN1', country: 'Japan', tier: 1, url: 'football-data.co.uk/japanm.php' },
  
  // ==========================================================================
  // SOUTH KOREA
  // ==========================================================================
  { id: '42', name: 'K League 1', code: 'KOR1', country: 'South Korea', tier: 1, url: 'football-data.co.uk/koream.php' },
  
  // ==========================================================================
  // AUSTRALIA
  // ==========================================================================
  { id: '43', name: 'A-League', code: 'AUS1', country: 'Australia', tier: 1, url: 'football-data.co.uk/australiam.php' },
];

/**
 * Get leagues grouped by country
 */
export function getLeaguesByCountry(): Record<string, League[]> {
  return allLeagues.reduce((acc, league) => {
    if (!acc[league.country]) {
      acc[league.country] = [];
    }
    acc[league.country].push(league);
    return acc;
  }, {} as Record<string, League[]>);
}

/**
 * Get leagues by tier
 */
export function getLeaguesByTier(): Record<number, League[]> {
  return allLeagues.reduce((acc, league) => {
    if (!acc[league.tier]) {
      acc[league.tier] = [];
    }
    acc[league.tier].push(league);
    return acc;
  }, {} as Record<number, League[]>);
}

/**
 * Get top tier leagues only
 */
export function getTopTierLeagues(): League[] {
  return allLeagues.filter(league => league.tier === 1);
}

