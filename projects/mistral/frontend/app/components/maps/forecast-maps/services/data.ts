export interface KeyValuePair {
    key: string;
    value: string;
}

export const Fields: KeyValuePair[] = [
    {key: 'prec3', value: 'Accumulated total prec. 3h (Kg/mq)'},
    {key: 'prec6', value: 'Accumulated total prec. 6h (Kg/mq)'},
    {key: 't2m', value: 'Temperature at 2 meters (C°)'},
    {key: 'wind', value: 'Wind at 10 meters (m/s)'},
    {key: 'cloud', value: 'Cloud coverage (%)'},
    {key: 'cloud_hml', value: 'Cloud coverage high, medium, low (%)'},
    {key: 'humidity', value: 'Relative humidity (%)'},
    {key: 'snow3', value: 'Accumulated total snow prec. 3h (Kg/mq)'},
    {key: 'snow6', value: 'Accumulated total snow prec. 6h (Kg/mq)'}
];

export const FlashFloodFFields: KeyValuePair[] = [
    {key: 'percentile', value: 'Flash Flood - 6h precipitation percentiles (mm)'},
    {key: 'probability', value: 'Flash Flood - 6h precipitation probability (%)'}
];

export const Levels_pe: KeyValuePair[] = [
    {key: '1', value: '1'},
    {key: '10', value: '10'},
    {key: '25', value: '25'},
    {key: '50', value: '50'},
    {key: '75', value: '75'},
    {key: '99', value: '99'}
];

export const Levels_pr: KeyValuePair[] = [
    {key: '5', value: '5'},
    {key: '10', value: '10'},
    {key: '20', value: '20'},
    {key: '50', value: '50'}
];

export const Runs: KeyValuePair[] = [
    {key: '00', value: '00'},
    {key: '12', value: '12'},
];

export const Resolutions: KeyValuePair[] = [
    {key: 'lm2.2', value: '2.2'},
    {key: 'lm5', value: '5'}
];

export const Platforms: KeyValuePair[] = [
    {key: 'GALILEO', value: 'GALILEO'},
    {key: 'MEUCCI', value: 'MEUCCI'}
];

export const Envs: KeyValuePair[] = [
    {key: 'PROD', value: 'PROD'},
    {key: 'DEV', value: 'DEVEL'}
];

export const Areas: KeyValuePair[] = [
    {key:'Italia', value:'Italy'},
    {key:'Nord_Italia', value:'Northern Italy'},
    {key:'Centro_Italia', value:'Central Italy'},
    {key:'Sud_Italia', value:'Southern Italy'},
    {key:'Area_Mediterranea', value:'Mediterranean region'}
];



