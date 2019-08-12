export class FormData {
    datasets: string[] = [];
    filters: Filters<string, any>[] = [];
    postprocessors: string[] = [];

    clear() {
        this.datasets = [];
        this.filters = [];
        this.postprocessors = [];
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
    description ?: string = '';
}
