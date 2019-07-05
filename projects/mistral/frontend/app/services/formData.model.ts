export class FormData {
    datasets: string[] = [];
    filters: Filter = {};
}

export class Filter {
    origin?: string = '';
    product?: string = '';
    reftime?: string = '';
    level?: string = '';
}

export class Dataset {
    id: string = '';
    description?: string = '';
}
