export class FormData {
    datasets: string[] = [];
    filters: Filters<string, any> = null;

    clear() {
        this.datasets = [];
        this.filters = null;
    }
}

/**
 * Expected generic key-value pair
 *
 * origin?: any;
 * product?: any;
 * reftime?: any;
 * level?: any;
 */
export interface Filters<T, U> {
    key: T;
    value: U;
}

export class Dataset {
    id: string = '';
    description?: string = '';
}
