export class FormData {
    datasets: string[] = [];
    filters: Filters<string, any>[] = [];

    clear() {
        this.datasets = [];
        this.filters = [];
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
    name: T;
    values: Array<U>;
    query: string;
}

export class Dataset {
    id: string = '';
    description?: string = '';
}
