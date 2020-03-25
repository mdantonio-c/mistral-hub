import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { FormBuilder, FormGroup, FormArray, FormControl, Validators } from '@angular/forms';
import { FormDataService } from "@app/services/formData.service";
import { DataService } from "@app/services/data.service";
import { NotificationService } from '@rapydo/services/notification';

@Component({
    selector: 'step-postprocess',
    templateUrl: './step-postprocess.component.html'
})
export class StepPostprocessComponent implements OnInit {
    title = 'Choose a post-processing';
    form: FormGroup;
    vars = [];
    templates = [];
    space_crop_boundings = [
        {
            code: 'ilon',
            desc: 'Initial Lon',
            validators: [
                Validators.min(-180),
                Validators.max(180)
            ]
        },
        {
            code: 'ilat',
            desc: 'Initial Lat',
            validators: [
                Validators.min(-90),
                Validators.max(90)
            ]
        },
        {
            code: 'flon',
            desc: 'Final Lon',
            validators: [
                Validators.min(-180),
                Validators.max(180)
            ]
        },
        {
            code: 'flat',
            desc: 'Final Lat',
            validators: [
                Validators.min(-90),
                Validators.max(90)
            ]
        },
    ];

    space_grid_boundings = [
        {
            code: 'x-min',
            desc: 'Initial Lon',
            validators: [
                Validators.min(-180),
                Validators.max(180)
            ]
        },
        {
            code: 'y-min',
            desc: 'Initial Lat',
            validators: [
                Validators.min(-90),
                Validators.max(90)
            ]
        },
        {
            code: 'x-max',
            desc: 'Final Lon',
            validators: [
                Validators.min(-180),
                Validators.max(180)
            ]
        },
        {
            code: 'y-max',
            desc: 'Final Lat',
            validators: [
                Validators.min(-90),
                Validators.max(90)
            ]
        },
    ];

    interpolation_nodes = [
        {
            code: 'nx',
            desc: 'nx',
            validators: [
                Validators.min(0)
            ]
        },
        {
            code: 'ny',
            desc: 'ny',
            validators: [
                Validators.min(0)
            ]
        }
    ];
    
    timeRanges = [
    {
        code: -1,
        desc: '-'
    },
    {
        code: 0,
        desc: 'Average'
    },
    {
        code: 1,
        desc: 'Accumulation'
    },
    {
        code: 2,
        desc: 'Maximum'
    },
    {
        code: 3,
        desc: 'Minimum'
    }];
    
    stepIntervals = ["-", "hour", "day", "month", "year"];
    
    interpolationTypes = ["-", "near", "bilin", "average", "min", "max"];

    cropTypes = [        
        {
            code: 0,
            desc: 'coord'
        },
        {
            code: 1,
            desc: 'bbox'
        }
    ];

    selectedCropType = {
            code: 0,
            desc: 'coord'
        };

    formatTypes = ['-','json'];    

    selectedInputTimeRange;
    selectedOutputTimeRange;
    selectedStepInterval;
    selectedInterpolationType;
    selectedConversionFormat;

    constructor(private formBuilder: FormBuilder,
        private router: Router,
        private route: ActivatedRoute,
        private formDataService: FormDataService,
        private dataService: DataService,        
        private notify: NotificationService) {
        this.form = this.formBuilder.group({
            derived_variables: new FormArray([]),
            space_type: [],
            space_crop: new FormArray([]),
            space_grid: new FormArray([]),            
            gridInterpolationType: ['template'],
            gridTemplateFile: new FormControl(''),
            interpolationNodes: new FormArray([]),
            conversionFormat: ['json'],
            timeStep: new FormControl(),
            templates: []
        });
    }

    private buildDerivedVariables() {
        const av = this.formDataService.getFormData().postprocessors.filter(p => p.type === 'derived_variables');
        let presetVariables = [];
        if (av && av.length) {
            presetVariables = av[0].variables;
        }
        this.vars.map(v => {
            const control = this.formBuilder.control(presetVariables.includes(v.code));
            (this.form.controls.derived_variables as FormArray).push(control);
        });
    }

    private buildTimePostProcess(){
        const pt = this.formDataService.getFormData().postprocessors.filter(p => p.type === 'statistic_elaboration');
        if (pt && pt.length){
            this.selectedStepInterval = pt[0].interval; //'interval': this.selectedStepInterval,
            this.form.controls['timeStep'].setValue(pt[0].step); //'step': this.form.value.timeStep
            this.selectedInputTimeRange = this.timeRanges.filter(t => t.code == pt[0]['input-timerange'])[0];
            this.selectedOutputTimeRange = this.timeRanges.filter(t => t.code == pt[0]['output-timerange'])[0];
        }else{
            this.selectedStepInterval = "-";
            this.selectedInputTimeRange = {
                code: -1,
                desc: '-'
            };
            
            this.selectedOutputTimeRange =  {
                code: -1,
                desc: '-'
            };
        }

    }

    private buildSpaceCrop() {
        this.space_crop_boundings.map(bound => {
            const control = this.formBuilder.control(0, bound.validators);
            (this.form.controls.space_crop as FormArray).push(control);
        })
    }

    private buildSpaceGrid() {
        this.space_grid_boundings.map(bound => {
            const control = this.formBuilder.control(0, bound.validators);
            (this.form.controls.space_grid as FormArray).push(control);
        })
    }

    private buildNodesInterpolation() {
        this.interpolation_nodes.map(node => {
            const control = this.formBuilder.control(0, node.validators);
            (this.form.controls.interpolationNodes as FormArray).push(control);
        })
    }

    private buildTemplates(){
        this.templates = [];
        this.dataService.getTemplates().subscribe(
            data => {
                   
                    for (let type of data.data)
                        {
                            for (let file of type.files)
                            {   let filepath = file.split('/');
                                let label = filepath[filepath.length-1];
                                this.templates.push({'label':label,'filepath': file, 'format':type.type});
                            }
                        }
            },
            error => {
                this.notify.showError('Unable to load templates');
            }
            )
    }

    ngOnInit() {
        window.scroll(0, 0);
        this.dataService.getDerivedVariables().subscribe(
            data => {
                this.vars = data;
                this.buildDerivedVariables();
            },
            error => {
                this.notify.showError('Unable to load derived variables configuration');
            }
        )
        this.buildTemplates();
        this.buildTimePostProcess();
        this.selectedInterpolationType = "-";
        this.selectedConversionFormat = '-';   
        this.buildSpaceCrop();
        this.buildSpaceGrid();
        this.buildNodesInterpolation();
    }

    loadFile(files: FileList){
        if (files.length == 1){
            let file :File = files[0];
            console.log(file);
            this.uploadFile(file);

        }
    }
    uploadFile(file: File){
        this.dataService.uploadTemplate(file).subscribe(
            data => {
                     this.buildTemplates();
                    // this.form.controls['templates'].setValue(file.name);


                    },
            error => {this.notify.showError(error.error.Response.errors[0]);}
            );
    }

    private save() {
        if (!this.form.valid) {
            return false;
        }
        const selectedProcessors = [];
        // derived variables
        const selectedDerivedVariables = this.form.value.derived_variables
            .map((v, i) => v ? this.vars[i].code : null)
            .filter(v => v !== null);
        if (selectedDerivedVariables && selectedDerivedVariables.length) {
            selectedProcessors.push({
                type: 'derived_variables',
                variables: selectedDerivedVariables
            });
        }

        // Time post processing
        if (this.selectedInputTimeRange.code != null && this.selectedInputTimeRange.code != -1
            && this.selectedOutputTimeRange.code != null && this.selectedOutputTimeRange.code != -1
            && this.form.value.timeStep != null
            && this.selectedStepInterval != null && this.selectedStepInterval != '-'){
            selectedProcessors.push(this.calculateTimePostProcessor());
        }

        // push space processor object in selectedProcessors
        const selectedSpaceProcessor = this.form.value.space_type;
        if (selectedSpaceProcessor && selectedSpaceProcessor.length) {
            switch (selectedSpaceProcessor) {
                case 'crop': {
                    selectedProcessors.push(this.calculateSpaceCrop());
                    break;
                }

                case 'grid': {
                    selectedProcessors.push(this.calculateSpaceGridCoord());
                    break;
                }

                case 'points': {
                    selectedProcessors.push(this.calculateSpacePoints());
                    break;
                }
            }

        }

        this.formDataService.setPostProcessor(selectedProcessors);
        if (this.selectedConversionFormat != null && this.selectedConversionFormat != ' '){
            this.formDataService.setOutputFormat(this.selectedConversionFormat);
        }
        return true;
    }


    calculateSpaceCrop() {
        const boundings = {}
        this.form.value.space_crop.map((value, i) => {
            boundings[this.space_crop_boundings[i].code] = value;
        })
        
        return {
            'type': 'grid_cropping',
            'sub-type': this.selectedCropType.desc,
            'boundings': boundings
        }
    }

    calculateSpaceGridCoord(){
        const boundings = {};
        const nodes = {};

        if (this.form.value.gridInterpolationType =="area")
        {
               this.form.value.space_grid.map((value, i) => {
                boundings[this.space_grid_boundings[i].code] = value;
            });
            this.form.value.interpolationNodes.map((value, i) => {
                nodes[this.interpolation_nodes[i].code] = value;
            })

         return {
             'type': 'grid_interpolation',
                'sub_type': this.selectedInterpolationType,
               'boundings': boundings,
               'nodes': nodes
            } 
        }
         if (this.form.value.gridInterpolationType =="template")
         {
            
            return {
                'type': 'grid_interpolation',
                 'template': this.form.value.templates,
                'sub_type': this.selectedInterpolationType,
            }
         }
        

    }

    calculateSpacePoints(){

        return {
            'type' : 'spare_point_interpolation',
            'coord-filepath': this.form.value.templates,
            'format' : this.templates.find(t => t.filepath == this.form.value.templates).format,
             'sub_type': this.selectedInterpolationType,
            
        }
    }

    calculateTimePostProcessor(){
        return {
            'type': 'statistic_elaboration',
            'input-timerange': this.selectedInputTimeRange.code,
            'output-timerange': this.selectedOutputTimeRange.code,
            'interval': this.selectedStepInterval,
            'step': this.form.value.timeStep
        }
    }

    goToPrevious() {
        // Navigate to the dataset page
        this.router.navigate(
            ['../', 'filters'], { relativeTo: this.route });
    }

    goToNext() {
        if (this.save()) {
            // Navigate to the postprocess page
            this.router.navigate(
                ['../', 'submit'], { relativeTo: this.route });
        }
    }

    setInputRange(inRange){
        this.selectedInputTimeRange = inRange;
    }

    setOutputRange(outRange){
        this.selectedOutputTimeRange = outRange;
    }

    setStepInterval(interval){
        this.selectedStepInterval = interval;
    }

    setCropType(cropType){
        this.selectedCropType = cropType;
    }

    setInterpolationType(interpolationType){
        this.selectedInterpolationType = interpolationType;
    }

    setConversionFormat(format){
        this.selectedConversionFormat = format;
    }

}
