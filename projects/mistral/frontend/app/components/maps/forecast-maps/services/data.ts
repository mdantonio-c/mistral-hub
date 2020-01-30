export interface KeyValuePair {
    key: string;
    value: string;
}

export const Fields: KeyValuePair[] = [
    {key: 'prec3', value: 'Accumulated total prec. 3h (Kg/mq)'},
    {key: 'prec6', value: 'Accumulated total prec. 6h (Kg/mq)'},
    {key: 't2m', value: 'Temperature at 2 meters (C°)'},
    {key: 'wind', value: 'Wind at 10 meters (m/s)'},
    {key: 'cloud', value: 'Cloud coverage (%%)'},
    {key: 'cloud_hml', value: 'Cloud coverage high, medium, low (%%)'},
    {key: 'humidity', value: 'Relative humidity (%%)'},
    {key: 'snow3', value: 'Accumulated total snow prec. 3h (Kg/mq)'},
    {key: 'snow6', value: 'Accumulated total snow prec. 6h (Kg/mq)'}
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
    {key: 'galileo_meteo_download/OPE/web', value: 'GALILEO'},
    {key: 'meucci_meteo_download/OPE/web', value: 'MEUCCI'}
];

export const Envs: KeyValuePair[] = [
    {key: 'PROD', value: 'PROD'},
    {key: 'DEV', value: 'DEVEL'}
];

export const Areas: KeyValuePair[] = [
    {key:'Italia', value:'Italy'},
    {key:'Nord Italia', value:'Northern Italy'},
    {key:'Centro_Italia', value:'Central Italy'},
    {key:'Sud_Italia', value:'Southern Italy'},
    {key:'Area_Mediterranea', value:'Mediterranean region'}
];



